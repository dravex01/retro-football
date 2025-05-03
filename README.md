# Retro Side Football

A lightweight 2D side-view football (soccer) game built with Pygame. Includes single-player mode against a Q-learning based AI trainer and two-player local mode. Matches and training data are stored in SQLite databases.

## Features

- **Single-player vs AI**: Play against an AI trained with Q-learning. AI adapts over matches and can be trained in accelerated background mode.
- **Two-player local mode**: Compete with a friend on the same keyboard.
- **Skin selection**: Choose from 8 different player skins for each participant.
- **Physics-based ball movement**: Gravity, bounce, friction, and air resistance for realistic ball behavior.
- **Match history**: Save and view past match results stored in `match_history.db`.
- **AI training data**: Log AI experience and Q-table to `ai_states.db`.

## Requirements

- Python 3.7+
- Pygame

## Installation

1. Clone the repository or download the source files.
2. Install dependencies:
   ```bash
   pip install pygame
   ```
3. Place the following assets in the working directory:
   - `player1.png` through `player8.png` (40×40 px player skins)
   - `ball.png` (20×20 px ball image)

## File Structure

```
├── foci.py           # Main game loop and Pygame interface
├── ai_learning.py    # Q-learning AI trainer implementation
├── match_history.db  # SQLite DB for saving match results (auto-created)
├── ai_states.db      # SQLite DB for AI training data and Q-table (auto-created)
├── player1.png       # ... player8.png    # Player skin assets
└── ball.png                              # Ball asset
```

## Usage

### Running the Game

```bash
python foci.py
```

### Game Modes

- **Single-player**: Press `1` at the menu to play against the AI.
- **Two-player**: Press `2` at the menu for local multiplayer.
- **History**: Press `H` at the menu to view saved match history.
- **Quit**: Press `ESC` at any time to exit.

### Controls

| Player 1              | Single-player AI plays Player 2 |
|-----------------------|---------------------------------|
| Move left: `A`       | AI controlled                   |
| Move right: `D`      |                                 |
| Jump: `W`            |                                 |
| Kick: `S`            |                                 |
|                       |                                 |
| Player 2 (multiplayer)|                                 |
| Move left: `←`       |                                 |
| Move right: `→`      |                                 |
| Jump: `↑`            |                                 |
| Kick: `↓`            |                                 |
| Pause: `P`           | Pause/resume single-player mode |
| Quit to menu: `Q`    |                                 |

During skin selection, use `←` / `→` to cycle skins and `ENTER` to confirm. Press `Q` to go back.

## AI Trainer

### Background Training Mode

Press `F1` during gameplay to stop the accelerated background training thread. The AI trainer runs continuously in a daemon thread when the game starts:

- **Accelerated training** simulates two parallel environments to populate the Q-table.
- Q-table is updated every 10 episodes, with epsilon decay for exploration.
- Press `F2` (if enabled) to manually save the Q-table mid-session.

### Q-learning Parameters

- **Learning rate (α)**: Adaptively increases after wins, decreases after losses.
- **Discount factor (γ)**: 0.9
- **Epsilon (ε)**: Starts at 0.3, decays toward a minimum of 0.05.
- **Reward function**: +5 for goals, -5 for own goals, small proximity rewards for ball interaction.

## Databases

### `match_history.db`

- Table: `matches(id, name, score_left, score_right, timestamp)`
- Inser­tion occurs after match end when a name is entered.

### `ai_states.db`

- Table: `ai_training(id, state, action, reward, next_state, timestamp)`
- Table: `q_table(state, action, value)` for persistent Q-values.

## Contributing

Feel free to open issues or submit pull requests to improve gameplay, AI behavior, or add features.

## License

MIT License.

