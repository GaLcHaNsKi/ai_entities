#!/usr/bin/env python3
"""
train.py — headless PPO обучение RL-агента в экосистемной симуляции.

Использование:
    python train.py --agent herbivore --steps 200000
    python train.py --agent predator  --steps 500000 --lr 0.0001
    python train.py --agent herbivore --resume models/herbivore_ppo.zip
    python train.py --agent predator  --steps 300000 --opponent-model models/herbivore_ppo.zip --opponent-ratio 0.5
    python train.py --agent herbivore --steps 200000 --gpu  # Максимум GPU оптимизации
"""

import argparse
import os
import sys
import time
import copy

def parse_args():
    p = argparse.ArgumentParser(description="Train RL agent for AI Entities simulation")
    p.add_argument("--agent", choices=["herbivore", "predator", "smart"], default="herbivore",
                   help="Type of creature to train (default: herbivore)")
    p.add_argument("--steps", type=int, default=200_000,
                   help="Total training timesteps (default: 200000)")
    p.add_argument("--lr", type=float, default=3e-4,
                   help="Learning rate (default: 3e-4)")
    p.add_argument("--batch-size", type=int, default=64,
                   help="Minibatch size (default: 64)")
    p.add_argument("--n-steps", type=int, default=2048,
                   help="Steps per rollout (default: 2048)")
    p.add_argument("--max-episode-steps", type=int, default=4000,
                   help="Max steps per episode (default: 4000)")
    p.add_argument("--save-dir", type=str, default="models",
                   help="Directory to save trained models (default: models/)")
    p.add_argument("--log-dir", type=str, default="logs",
                   help="Tensorboard log directory (default: logs/)")
    p.add_argument("--resume", type=str, default=None,
                   help="Path to model .zip to resume training from")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed (default: 42)")
    p.add_argument("--device", type=str, default="auto",
                   help="PyTorch device: auto|cpu|cuda (default: auto)")
    p.add_argument("--opponent-model", type=str, default=None,
                   help="Path to trained model .zip for opponent creatures (e.g. herbivore model when training predator)")
    p.add_argument("--opponent-ratio", type=float, default=0.5,
                   help="Fraction of opponents using RL model vs heuristic (default: 0.5)")
    p.add_argument("--n-envs", type=int, default=0,
                   help="Number of parallel environments (0=auto, based on CPU cores)")
    p.add_argument("--curriculum-smart", action="store_true",
                   help="Enable 3-phase curriculum for smart agent training")
    
    return p.parse_args()


def main():
    args = parse_args()
    
    # Ленивый импорт — чтобы --help работал без torch
    try:
        from stable_baselines3 import PPO
        from stable_baselines3.common.callbacks import (
            CheckpointCallback, EvalCallback, CallbackList
        )
        from stable_baselines3.common.monitor import Monitor
        from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
    except ImportError:
        print("ERROR: stable-baselines3 not installed.")
        print("Run:  pip install 'stable-baselines3>=2.1.0' 'gymnasium>=0.29.0' 'torch>=2.0.0'")
        sys.exit(1)
    
    from ai.gym_env import SingleAgentEnv
    from core.config import Presets
    
    # --- Число параллельных сред ---
    if args.n_envs <= 0:
        import multiprocessing
        n_envs = max(1, multiprocessing.cpu_count() - 1)
    else:
        n_envs = args.n_envs
    
    # n_steps должен делиться на n_envs для batch
    # Минимум 512 на среду — иначе разреженные награды не работают
    effective_n_steps = max(args.n_steps // n_envs, 512)
    # batch_size не может быть больше n_steps * n_envs
    effective_batch = min(args.batch_size, effective_n_steps * n_envs)
    
    print("=" * 60)
    print(f"  AI Entities — RL Training ({args.agent})")
    print("=" * 60)
    print(f"  Total steps   : {args.steps:,}")
    print(f"  Learning rate  : {args.lr}")
    print(f"  Batch size     : {effective_batch}")
    print(f"  Rollout steps  : {effective_n_steps} × {n_envs} envs = {effective_n_steps * n_envs}")
    print(f"  Episode max    : {args.max_episode_steps}")
    print(f"  Device         : {args.device}")
    print(f"  Seed           : {args.seed}")
    print(f"  Parallel envs  : {n_envs}")
    print(f"  Resume from    : {args.resume or 'scratch'}")
    if args.opponent_model:
        print(f"  Opponent model : {args.opponent_model}")
        print(f"  Opponent ratio : {args.opponent_ratio:.0%}")
    print("=" * 60)
    
    # --- Создаём директории ---
    os.makedirs(args.save_dir, exist_ok=True)
    os.makedirs(args.log_dir, exist_ok=True)
    
    # --- Среда ---
    base_config = Presets.balanced()

    def build_smart_phase_config(phase_idx: int):
        cfg = copy.deepcopy(base_config)

        # Phase 1 (Survival): много еды, мало угроз
        if phase_idx == 1:
            cfg.world.plant_count = int(cfg.world.plant_count * 1.5)
            cfg.world.tree_count = int(cfg.world.tree_count * 1.3)
            cfg.world.stone_count = int(cfg.world.stone_count * 1.25)
            cfg.world.copper_count = int(cfg.world.copper_count * 1.25)
            cfg.world.iron_count = int(cfg.world.iron_count * 1.15)
            cfg.predators.count = max(1, int(cfg.predators.count * 0.35))
            cfg.herbivores.count = int(cfg.herbivores.count * 1.2)

        # Phase 2 (Economy): умеренные угрозы, акцент на добычу/крафт
        elif phase_idx == 2:
            cfg.world.plant_count = int(cfg.world.plant_count * 1.2)
            cfg.world.tree_count = int(cfg.world.tree_count * 1.35)
            cfg.world.stone_count = int(cfg.world.stone_count * 1.35)
            cfg.world.copper_count = int(cfg.world.copper_count * 1.4)
            cfg.world.iron_count = int(cfg.world.iron_count * 1.35)
            cfg.predators.count = max(2, int(cfg.predators.count * 0.7))

        # Phase 3 (Full): полноценная конкурентная среда
        else:
            cfg = copy.deepcopy(base_config)

        return cfg

    def make_env_with_config(config, opponent_ratio):
        def _init():
            env = SingleAgentEnv(
                agent_type=args.agent,
                config=config,
                max_steps=args.max_episode_steps,
                opponent_model_path=args.opponent_model,
                opponent_ratio=opponent_ratio,
            )
            env = Monitor(env)
            return env
        return _init

    def make_vec_envs(config, opponent_ratio):
        if n_envs > 1:
            train_env = SubprocVecEnv([make_env_with_config(config, opponent_ratio) for _ in range(n_envs)])
            eval_env = SubprocVecEnv([make_env_with_config(config, opponent_ratio)])
        else:
            train_env = DummyVecEnv([make_env_with_config(config, opponent_ratio)])
            eval_env = DummyVecEnv([make_env_with_config(config, opponent_ratio)])
        return train_env, eval_env

    curriculum_enabled = args.curriculum_smart and args.agent == "smart"
    if args.curriculum_smart and args.agent != "smart":
        print("[warn] --curriculum-smart is only used with --agent smart. Running normal training.")

    initial_config = build_smart_phase_config(1) if curriculum_enabled else base_config
    initial_opponent_ratio = args.opponent_ratio if not curriculum_enabled else min(args.opponent_ratio, 0.35)
    vec_env, eval_env = make_vec_envs(initial_config, initial_opponent_ratio)
    
    # --- Модель ---
    if args.resume and os.path.exists(args.resume):
        print(f"\nResuming from {args.resume} ...")
        model = PPO.load(
            args.resume,
            env=vec_env,
            device=args.device,
            learning_rate=args.lr,
            n_steps=effective_n_steps,
            batch_size=effective_batch,
        )
    else:
        print("\nCreating new PPO model ...")

        # Smart agents: bigger net, lower entropy (continuous mode selection needs focused std)
        if args.agent == "smart":
            policy_kwargs = dict(
                net_arch=dict(pi=[256, 256], vf=[256, 256]),
                log_std_init=-2.0,  # std≈0.135 — very low for precise mode selection
            )
            ent_coef = 0.0       # Entropy bonus fights mode convergence in continuous space
            lr = args.lr if args.lr != 3e-4 else 5e-5  # Even lower LR for smart agent
        else:
            # Lower std from start by reducing log_std_init and entropy
            policy_kwargs = dict(
                log_std_init=-1.0,  # std≈0.37 — reduces exploration
            )
            ent_coef = 0.001      # Much lower entropy: prevents std from growing
            lr = args.lr

        model = PPO(
            policy="MlpPolicy",
            env=vec_env,
            learning_rate=lr,
            n_steps=effective_n_steps,
            batch_size=effective_batch,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            clip_range_vf=None,  # Disable VF clipping for better value stability
            ent_coef=ent_coef,
            vf_coef=0.9 if args.agent == "smart" else 0.7,  # Enforce value stability harder for smart
            max_grad_norm=0.5,
            verbose=1,
            seed=args.seed,
            device=args.device,
            tensorboard_log=args.log_dir,
            policy_kwargs=policy_kwargs,
        )
    
    # --- Обучение ---
    t0 = time.time()
    model_name = f"{args.agent}_ppo"
    print(f"\nTraining for {args.steps:,} steps...\n")

    def run_phase(phase_name: str, phase_steps: int, train_env, eval_env, keep_timestep: bool):
        checkpoint_cb = CheckpointCallback(
            save_freq=max(phase_steps // 10, 3000),
            save_path=args.save_dir,
            name_prefix=f"{model_name}_{phase_name}",
            verbose=1,
        )

        best_dir = os.path.join(args.save_dir, f"best_{args.agent}")
        os.makedirs(best_dir, exist_ok=True)

        eval_cb = EvalCallback(
            eval_env,
            best_model_save_path=best_dir,
            log_path=args.log_dir,
            eval_freq=max(phase_steps // 20, 2500),
            n_eval_episodes=5,
            deterministic=True,
            verbose=1,
        )

        callbacks = CallbackList([checkpoint_cb, eval_cb])

        model.set_env(train_env)
        model.learn(
            total_timesteps=phase_steps,
            callback=callbacks,
            progress_bar=True,
            reset_num_timesteps=not keep_timestep,
        )

    if curriculum_enabled:
        phase_specs = [
            ("phase1_survival", 0.25, 1, min(args.opponent_ratio, 0.35)),
            ("phase2_economy", 0.35, 2, min(max(args.opponent_ratio, 0.45), 0.65)),
            ("phase3_full", 0.40, 3, max(args.opponent_ratio, 0.65)),
        ]

        # Корректируем округления, чтобы сумма была ровно args.steps
        phase_steps = [int(args.steps * ratio) for _, ratio, _, _ in phase_specs]
        phase_steps[-1] += args.steps - sum(phase_steps)

        print("[curriculum] Smart curriculum enabled: 3 phases")

        # Фаза 1 уже создана выше как initial env
        run_phase(
            phase_specs[0][0],
            phase_steps[0],
            vec_env,
            eval_env,
            keep_timestep=False,
        )
        vec_env.close()
        eval_env.close()

        # Фазы 2-3
        for idx in [1, 2]:
            phase_name, _, phase_id, opp_ratio = phase_specs[idx]
            cfg = build_smart_phase_config(phase_id)
            vec_env, eval_env = make_vec_envs(cfg, opp_ratio)
            print(f"[curriculum] {phase_name}: steps={phase_steps[idx]:,}, opponent_ratio={opp_ratio:.2f}")
            run_phase(
                phase_name,
                phase_steps[idx],
                vec_env,
                eval_env,
                keep_timestep=True,
            )
            vec_env.close()
            eval_env.close()
    else:
        run_phase("main", args.steps, vec_env, eval_env, keep_timestep=False)
        vec_env.close()
        eval_env.close()
    
    elapsed = time.time() - t0
    
    # --- Сохранение ---
    final_path = os.path.join(args.save_dir, f"{model_name}.zip")
    model.save(final_path)
    
    print("\n" + "=" * 60)
    print(f"  Training complete!")
    print(f"  Time elapsed : {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  Model saved  : {final_path}")
    print(f"  Tensorboard  : tensorboard --logdir {args.log_dir}")
    print("=" * 60)
    
    # Cleanup handled per phase above


if __name__ == "__main__":
    main()
