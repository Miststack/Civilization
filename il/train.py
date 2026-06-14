"""
从 data/il_expert.npz 训练 PolicyNet，保存 data/il_policy.pt。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset, random_split

from engine.game import GameConfig, GameState
from il.encoding import ACTION_DIM, STATE_DIM
from il.learned_agent import LearnedAgent
from il.model import PolicyNet, masked_cross_entropy


def evaluate_agent(agent: LearnedAgent, seeds: range, map_size: int, turns: int) -> float:
    scores: list[int] = []
    for seed in seeds:
        state = GameState(GameConfig(map_size=map_size, total_turns=turns, seed=seed))
        while not state.is_terminal():
            state.do_turn(agent.choose(state))
        scores.append(state.score())
    return float(sum(scores) / len(scores)) if scores else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="模仿学习训练 PolicyNet")
    parser.add_argument("--data", type=str, default="data/il_expert.npz")
    parser.add_argument("--out", type=str, default="data/il_policy.pt")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden", type=int, default=256)
    parser.add_argument("--device", type=str, default=None, help="cuda / cpu，默认自动")
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--eval-seeds", type=int, default=10, help="训练后评估局数")
    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="从已有权重继续训练（如 data/il_policy.pt）",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=8,
        help="验证集准确率连续多少轮不提升则早停（0=关闭）",
    )
    parser.add_argument(
        "--select-by",
        choices=("val_acc", "game_score"),
        default="game_score",
        help="保存最佳权重的依据（推荐 game_score）",
    )
    parser.add_argument(
        "--eval-every",
        type=int,
        default=5,
        help="select-by=game_score 时每多少 epoch 评估对局得分",
    )
    args = parser.parse_args()

    data_path = Path(args.data)
    if not data_path.is_file():
        raise FileNotFoundError(f"缺少训练数据: {data_path}，请先运行 python -m il.record_expert")

    if args.device:
        device = torch.device(args.device)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("device:", device)

    raw = np.load(data_path)
    X = torch.tensor(raw["states"], dtype=torch.float32)
    y = torch.tensor(raw["actions"], dtype=torch.long)
    M = torch.tensor(raw["masks"], dtype=torch.float32)
    map_size = int(raw.get("map_size", 10))
    turns = int(raw.get("turns", 30))

    if X.shape[1] != STATE_DIM:
        raise ValueError(f"状态维度 {X.shape[1]} != 期望 {STATE_DIM}")

    n = len(X)
    n_val = max(1, int(n * args.val_ratio))
    n_train = n - n_val
    ds = TensorDataset(X, y, M)
    train_ds, val_ds = random_split(
        ds, [n_train, n_val], generator=torch.Generator().manual_seed(0)
    )
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    model = PolicyNet(state_dim=X.shape[1], hidden=args.hidden, action_dim=ACTION_DIM).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)

    start_epoch = 1
    best_val_acc = -1.0
    best_game_score = -1.0
    best_state = None
    no_improve = 0

    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.is_file():
            raise FileNotFoundError(f"找不到 resume 权重: {resume_path}")
        ckpt = torch.load(resume_path, map_location=device, weights_only=False)
        model.load_state_dict(ckpt["state_dict"])
        if int(ckpt.get("hidden", args.hidden)) != args.hidden:
            raise ValueError(
                f"checkpoint hidden={ckpt.get('hidden')} 与 --hidden={args.hidden} 不一致"
            )
        if ckpt.get("optimizer_state_dict") is not None:
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
        best_val_acc = float(ckpt.get("val_acc", -1.0))
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        start_epoch = int(ckpt.get("epoch", 0)) + 1
        print(f"已从 {resume_path} 恢复 (epoch={start_epoch - 1}, val_acc={best_val_acc:.3f})")

    end_epoch = start_epoch + args.epochs - 1
    eval_tmp_path = Path(args.out).with_suffix(".eval_tmp.pt")
    out_path = Path(args.out)

    for epoch in range(start_epoch, end_epoch + 1):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        for xb, yb, mb in train_loader:
            xb, yb, mb = xb.to(device), yb.to(device), mb.to(device)
            logits = model(xb)
            loss = masked_cross_entropy(logits, yb, mb)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            pred = logits.masked_fill(mb < 0.5, -1e9).argmax(dim=1)
            train_correct += int((pred == yb).sum().item())
            train_total += len(xb)
            train_loss += loss.item() * len(xb)

        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for xb, yb, mb in val_loader:
                xb, yb, mb = xb.to(device), yb.to(device), mb.to(device)
                logits = model(xb)
                pred = logits.masked_fill(mb < 0.5, -1e9).argmax(dim=1)
                val_correct += int((pred == yb).sum().item())
                val_total += len(xb)

        train_acc = train_correct / max(1, train_total)
        val_acc = val_correct / max(1, val_total)
        print(
            f"epoch {epoch:02d}/{end_epoch}  "
            f"loss={train_loss/max(1,train_total):.4f}  "
            f"train_acc={train_acc:.3f}  val_acc={val_acc:.3f}"
        )

        improved = False
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            if args.select_by == "val_acc":
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                improved = True

        if args.select_by == "game_score" and epoch % max(1, args.eval_every) == 0:
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "state_dim": int(X.shape[1]),
                    "action_dim": ACTION_DIM,
                    "hidden": args.hidden,
                },
                eval_tmp_path,
            )
            agent = LearnedAgent(weights_path=eval_tmp_path, device=str(device), top_k_rerank=8)
            game_mean = evaluate_agent(agent, range(min(20, args.eval_seeds)), map_size, turns)
            print(f"         game_score({min(20, args.eval_seeds)} seeds)={game_mean:.1f}")
            if game_mean > best_game_score:
                best_game_score = game_mean
                best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
                improved = True

        if improved:
            no_improve = 0
        else:
            no_improve += 1
            if args.patience > 0 and no_improve >= args.patience:
                print(f"早停于 epoch {epoch}（连续 {args.patience} 轮无提升）")
                break

    if best_state is None:
        best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "state_dim": int(X.shape[1]),
            "action_dim": ACTION_DIM,
            "hidden": args.hidden,
            "val_acc": best_val_acc,
            "game_score": best_game_score,
            "epoch": epoch,
        },
        out_path,
    )
    print(f"已保存权重 -> {out_path} (best val_acc={best_val_acc:.3f}, game_score={best_game_score:.1f})")

    agent = LearnedAgent(weights_path=out_path, device=str(device), top_k_rerank=8)
    eval_mean = evaluate_agent(agent, range(args.eval_seeds), map_size, turns)
    print(f"评估 {args.eval_seeds} 局平均终局分: {eval_mean:.1f}")


if __name__ == "__main__":
    main()
