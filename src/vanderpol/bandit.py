"""Small contextual-bandit baselines for smoke experiments."""

from __future__ import annotations

import numpy as np


class LinUCB:
    """Classic disjoint LinUCB with one linear model per action."""

    def __init__(
        self,
        n_actions: int,
        n_features: int,
        alpha: float = 0.75,
        ridge: float = 1.0,
    ):
        self.n_actions = int(n_actions)
        self.n_features = int(n_features)
        self.alpha = float(alpha)
        self.a = np.stack([ridge * np.eye(n_features) for _ in range(n_actions)])
        self.b = np.zeros((n_actions, n_features), dtype=float)

    def select(self, x: np.ndarray) -> int:
        x = np.asarray(x, dtype=float)
        scores = []
        for action in range(self.n_actions):
            inv = np.linalg.inv(self.a[action])
            theta = inv @ self.b[action]
            mean = float(theta @ x)
            bonus = self.alpha * float(np.sqrt(x @ inv @ x))
            scores.append(mean + bonus)
        return int(np.argmax(scores))

    def update(self, action: int, x: np.ndarray, reward: float) -> None:
        x = np.asarray(x, dtype=float)
        self.a[action] += np.outer(x, x)
        self.b[action] += float(reward) * x

    def fit_logged(self, contexts: np.ndarray, actions: np.ndarray, rewards: np.ndarray) -> None:
        for x, action, reward in zip(contexts, actions, rewards):
            self.update(int(action), x, float(reward))

    def predict_many(self, contexts: np.ndarray) -> np.ndarray:
        return np.asarray([self.select(x) for x in contexts], dtype=int)


def oracle_actions(reward_matrix: np.ndarray) -> np.ndarray:
    return np.asarray(np.argmax(reward_matrix, axis=1), dtype=int)


def mean_oracle_gap(
    chosen_actions: np.ndarray,
    reward_matrix: np.ndarray,
) -> float:
    oracle = np.max(reward_matrix, axis=1)
    chosen = reward_matrix[np.arange(len(chosen_actions)), chosen_actions]
    return float(np.mean(oracle - chosen))
