import sqlite3
import random
import math
from collections import defaultdict
from typing import Optional
from threading import Lock

class AITrainer:
    def __init__(self):
        self.conn = sqlite3.connect("ai_states.db", check_same_thread=False)
        self.create_tables()
        self.q_table = defaultdict(float)
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.3  # Kezdeti explorációs ráta
        self.batch_size = 100  # Batch méret adatbázis íráshoz
        self.batch_buffer = []
        self.load_q_table()
        self.epsilon_decay = 0.995
        self.win_streak = 0
        self.q_table_lock = Lock()

    def create_tables(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS ai_training (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state TEXT,
                    action TEXT,
                    reward REAL,
                    next_state TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Új tábla a Q-értékek tárolásához
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS q_table (
                    state TEXT,
                    action TEXT,
                    value REAL,
                    PRIMARY KEY (state, action)
                )''')
            
    def save_q_table(self):
        """Q-tábla mentése atomikus műveletben"""
        with self.q_table_lock, self.conn:
            self.conn.execute("DELETE FROM q_table")  # Régi adatok törlése
            batch_data = [
                (state, action, value)
                for (state, action), value in self.q_table.items()
            ]
            self.conn.executemany(
                "INSERT INTO q_table VALUES (?, ?, ?)",
                batch_data
            )        

    def discretize_position(self, value: int, step: int = 25) -> str:
        """Pozíció kvantálása a állapottér csökkentéséhez"""
        return str(int(math.floor(value / step)) * step)

    def get_state(self, ball_pos, player_pos, ball_velocity_x):
        dx = ball_pos[0] - player_pos[0]
        dy = ball_pos[1] - player_pos[1]
        return f"{self.discretize_position(dx)}|{self.discretize_position(dy)}|{int(ball_velocity_x)}"

    def calculate_reward(self, new_score_diff: int, prev_score_diff: int, 
                       goal_event: Optional[str]) -> float:
        """Reward számítás intelligensebb módon"""
        if goal_event == "goal_for":
            return 5.0  # Magas reward a gólért
        elif goal_event == "own_goal":
            return -5.0  # Nagy büntetés öngólért
        
        score_change = new_score_diff - prev_score_diff
        proximity_reward = 1 / (abs(score_change) + 1)  # Labda közelében járás
        
        # Összetett reward függvény
        return score_change * 0.5 + proximity_reward * 0.3

    def choose_action(self, state: str) -> str:
        """Akcióválasztás epsilon-greedy stratégiával"""
        actions = ["left", "right", "jump", "kick"]  # Kick hozzáadva
        if random.random() < self.epsilon:
            return random.choice(actions)
        
        ##actions = ["left", "right", "jump"]
        q_values = [self.q_table.get((state, a), 0) for a in actions]
        max_q = max(q_values)
        best_actions = [a for a, q in zip(actions, q_values) if q == max_q]
        return random.choice(best_actions) if best_actions else "jump"

    def update_q_table(self, state: str, action: str, reward: float, 
                      next_state: Optional[str]):
        """Q-tábla frissítése a Q-learning szabály szerint"""
        old_q = self.q_table.get((state, action), 0)
        max_next_q = max([self.q_table.get((next_state, a), 0) 
                        for a in ["left", "right", "jump", "kick"]]) if next_state else 0
        
        new_q = old_q + self.learning_rate * (
            reward + self.discount_factor * max_next_q - old_q
        )
        self.q_table[(state, action)] = new_q

    def log_training_data(self, state: str, action: str, 
                         reward: float, next_state: str):
        """Adatok batch mentése az adatbázisba"""
        self.batch_buffer.append((state, action, reward, next_state))
        
        if len(self.batch_buffer) >= self.batch_size:
            with self.conn:
                self.conn.executemany('''
                    INSERT INTO ai_training (state, action, reward, next_state)
                    VALUES (?, ?, ?, ?)
                ''', self.batch_buffer)
            self.batch_buffer.clear()

    def load_q_table(self):
        """Q-tábla betöltése a dedikált táblából"""
        with self.conn:
            cursor = self.conn.execute("SELECT state, action, value FROM q_table")
            for state, action, value in cursor.fetchall():
                self.q_table[(state, action)] = value
            print(f"🔁 Betöltött Q-állapotok: {len(self.q_table)}")

    def update_after_match(self, won: bool):
        """Paraméterek adaptív módosítása mérkőzés után"""
        if won:
            # Csökkentjük a véletlenszerűséget ha nyer
            self.win_streak += 1
            self.epsilon = max(0.05, self.epsilon * 0.95)
            self.learning_rate = min(0.2, self.learning_rate * 1.05)
        else:
            # Növeljük az explorációt ha veszít
            self.win_streak = 0
            self.epsilon = min(0.5, self.epsilon * 1.1)
            self.learning_rate = max(0.05, self.learning_rate * 0.95)

    def close(self):
        """Utolsó adatok mentése és kapcsolat bezárása"""
        self.save_q_table()
        if self.batch_buffer:
            with self.conn:
                self.conn.executemany('''
                    INSERT INTO ai_training (state, action, reward, next_state)
                    VALUES (?, ?, ?, ?)
                ''', self.batch_buffer)
        self.conn.close()

# Globális AI példány
ai_trainer = AITrainer()