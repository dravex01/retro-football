import pygame
import random
import sqlite3
import threading
import time
from ai_learning import ai_trainer  # Importáljuk az AI edzőt
from ai_learning import AITrainer, ai_trainer
from threading import Lock


pygame.init()

# Adatbázis kapcsolat
conn = sqlite3.connect("match_history.db")
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    score_left INTEGER,
    score_right INTEGER,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')
conn.commit()



# Képernyő beállítások
WIDTH, HEIGHT = 900, 450
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Retro Side Football")
clock = pygame.time.Clock()

# Színek
SKY_BLUE = (135, 206, 235)
GRASS_GREEN = (50, 160, 50)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
STADIUM_RED = (200, 0, 0)
LIGHT_GRAY = (200, 200, 200)

# Skin betöltés
SKINS = [f"player{i}.png" for i in range(1, 9)]
selected_skin_p1 = 0
selected_skin_p2 = 0
skin_selection_phase = 1
ai_skin_index = 0

# Fizikai állandók
GRAVITY = 0.5
JUMP_STRENGTH = -10
AIR_RESISTANCE = 0.99
GROUND_FRICTION = 0.9
BOUNCE_FRICTION = 0.7

# Kapuk
GOAL_HEIGHT = 150
left_goal_rect = pygame.Rect(0, HEIGHT - GOAL_HEIGHT, 10, GOAL_HEIGHT)
right_goal_rect = pygame.Rect(WIDTH - 10, HEIGHT - GOAL_HEIGHT, 10, GOAL_HEIGHT)

# Betűtípus
font = pygame.font.Font(None, 48)
small_font = pygame.font.Font(None, 36)

ai_wins = 0
human_wins = 0
reward_history = []

# Képek betöltése
def load_images():
    images = []
    for skin in SKINS:
        img = pygame.image.load(skin).convert_alpha()
        images.append(pygame.transform.scale(img, (40, 40)))
    return images

player_skins = load_images()
ball_img = pygame.transform.scale(pygame.image.load("ball.png").convert_alpha(), (20, 20))

class Player:
    def __init__(self, x, skin_index):
        self.image = player_skins[skin_index]
        self.rect = self.image.get_rect(midbottom=(x, HEIGHT))
        self.vel_y = self.vel_x = 0
        self.on_ground = False
        self.kicking = False

    def move(self, keys, left, right, jump, kick_key):
        self.kicking = keys[kick_key]
        self.vel_x = 0
        if keys[left]:
            self.rect.x -= 5
            self.vel_x = -5
        if keys[right]:
            self.rect.x += 5
            self.vel_x = 5
        if keys[jump] and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False
        self.rect.clamp_ip(screen.get_rect())

    def apply_gravity(self):
        self.vel_y += GRAVITY
        self.rect.y += self.vel_y
        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y = 0
            self.on_ground = True

    def check_collision(self, other):
        if self.rect.colliderect(other.rect):
            if self.vel_x > 0:
                self.rect.right = other.rect.left
            elif self.vel_x < 0:
                self.rect.left = other.rect.right

    def draw(self):
        screen.blit(self.image, self.rect)

class Ball:
    def __init__(self):
        self.image = ball_img
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.vel_x = random.choice([-4, 4])
        self.vel_y = 0

    def move(self):
        global score_left, score_right
        self.vel_y += GRAVITY
        self.vel_x *= AIR_RESISTANCE
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        if self.rect.bottom >= HEIGHT:
            self.rect.bottom = HEIGHT
            self.vel_y *= -BOUNCE_FRICTION
            self.vel_x *= GROUND_FRICTION

        if self.rect.top <= 0:
            self.rect.top = 0
            self.vel_y *= -1

        if left_goal_rect.collidepoint(self.rect.midleft):
            score_right += 1
            reset_positions()
        if right_goal_rect.collidepoint(self.rect.midright):
            score_left += 1
            reset_positions()

        if self.rect.x < 0:
            self.rect.x = 0
            self.vel_x *= -1

        if self.rect.x > WIDTH - self.rect.width:
            self.rect.x = WIDTH - self.rect.width
            self.vel_x *= -1

        if self.rect.y < 0:
            self.rect.y = 0
            self.vel_y *= -1

        if self.rect.y > HEIGHT - self.rect.height:
            self.rect.y = HEIGHT - self.rect.height
            self.vel_y *= -BOUNCE_FRICTION

    def check_collision(self, p):
        if p.kicking and p.rect.colliderect(self.rect.inflate(20, 20)):
            direction = 1 if p.rect.centerx < self.rect.centerx else -1
            self.vel_x = direction * 8 + p.vel_x * 0.7
            self.vel_y = -12

        if self.rect.colliderect(p.rect):
            overlap_x = min(self.rect.right, p.rect.right) - max(self.rect.left, p.rect.left)
            overlap_y = min(self.rect.bottom, p.rect.bottom) - max(self.rect.top, p.rect.top)

            if overlap_x < overlap_y:
                if self.rect.centerx < p.rect.centerx:
                    self.rect.right = p.rect.left
                    self.vel_x = -abs(self.vel_x) * BOUNCE_FRICTION
                else:
                    self.rect.left = p.rect.right
                    self.vel_x = abs(self.vel_x) * BOUNCE_FRICTION
                self.vel_x += p.vel_x * 0.5
            else:
                if self.rect.centery < p.rect.centery:
                    self.rect.bottom = p.rect.top
                    self.vel_y = -abs(self.vel_y) * BOUNCE_FRICTION
                else:
                    self.rect.top = p.rect.bottom
                    self.vel_y = abs(self.vel_y) * BOUNCE_FRICTION
                self.vel_y += p.vel_y * 0.5

    def draw(self):
        screen.blit(self.image, self.rect)

def reset_positions():
    global player1, player2, ball
    if game_mode == "single":
        player1 = Player(100, selected_skin_p1)
        player2 = Player(700, ai_skin_index)
    else:
        player1 = Player(100, selected_skin_p1)
        player2 = Player(700, selected_skin_p2)
    ball = Ball()

# Játék állapotok
game_state = "menu"
game_mode = None
score_left = score_right = 0
match_duration = 60
start_ticks = None
match_name_input = ""
paused = False

# Játékosok inicializálása
player1 = None
player2 = None
ball = None
reset_positions()

def draw_score():
    score_text = font.render(f"{score_left} : {score_right}", True, WHITE)
    bg_rect = score_text.get_rect(center=(WIDTH//2, 40))
    s = pygame.Surface((bg_rect.width + 40, bg_rect.height + 20), pygame.SRCALPHA)
    s.fill((0, 0, 0, 128))
    screen.blit(s, (bg_rect.x - 20, bg_rect.y - 10))
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 25))

def draw_field():
    # Sky gradient
    for y in range(HEIGHT//2):
        alpha = int(255 * (1 - y/(HEIGHT//2)))
        pygame.draw.line(screen, (SKY_BLUE[0], SKY_BLUE[1], SKY_BLUE[2], alpha), (0, y), (WIDTH, y))
    
    # Stadium
    pygame.draw.rect(screen, STADIUM_RED, (0, HEIGHT//2, WIDTH, HEIGHT//2))
    pygame.draw.rect(screen, GRASS_GREEN, (0, HEIGHT-100, WIDTH, 100))
    
    # Field lines
    pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT-50), 70, 3)
    pygame.draw.line(screen, WHITE, (WIDTH//2, HEIGHT-100), (WIDTH//2, HEIGHT), 3)
    
    # Goals
    pygame.draw.rect(screen, LIGHT_GRAY, left_goal_rect)
    pygame.draw.rect(screen, LIGHT_GRAY, right_goal_rect)


def accelerated_training():
    """Hibamentes folyamatos háttértanulás"""
    from ai_learning import AITrainer
    import time
    import math
    
    class TrainingEnv:
        def __init__(self):
            self.player = Player(700, random.randint(0,7))
            self.ball = Ball()
            self.scores = [0, 0]
            self.last_update = time.time()
        
        def reset(self):
            self.player.rect.midbottom = (700, HEIGHT)
            self.ball.rect.center = (WIDTH//2, HEIGHT//2)
            self.scores = [0, 0]

    local_trainer = AITrainer()
    envs = [TrainingEnv() for _ in range(2)]
    episode = 0
    
    print("Folyamatos tanulás aktív... (F1 - Leállítás)")
    
    while getattr(threading.current_thread(), "do_run", True):
        episode += 1
        start_time = time.time()
        
        for env in envs:
            # Állapotfrissítés
            current_state = local_trainer.get_state(
                ball_pos=env.ball.rect.center,
                player_pos=env.player.rect.center,
                ball_velocity_x=env.ball.vel_x
            )
            
            # Akció kiválasztása
            action = local_trainer.choose_action(current_state)
            
            # Akció végrehajtása
            if action == "left":
                env.player.rect.x = max(0, env.player.rect.x - 5)
            elif action == "right":
                env.player.rect.x = min(WIDTH-40, env.player.rect.x + 5)
            elif action == "jump" and env.player.on_ground:
                env.player.vel_y = JUMP_STRENGTH
            elif action == "kick":
                env.player.kicking = True
                if env.player.rect.colliderect(env.ball.rect.inflate(30,30)):
                    env.ball.vel_x = random.uniform(-15,15)
                    env.ball.vel_y = -12
            
            # Fizikai frissítések
            env.player.apply_gravity()
            env.ball.move()
            
            # Új állapot
            new_state = local_trainer.get_state(
                ball_pos=env.ball.rect.center,
                player_pos=env.player.rect.center,
                ball_velocity_x=env.ball.vel_x
            )
            
            # Reward számítás
            reward = local_trainer.calculate_reward(
                new_score_diff=env.scores[1]-env.scores[0],
                prev_score_diff=env.scores[1]-env.scores[0],
                goal_event=None
            )
            
            # Q-tábla frissítés
            local_trainer.update_q_table(
                state=current_state,
                action=action,
                reward=reward,
                next_state=new_state
            )
        
        # Paraméterfrissítés
        local_trainer.epsilon = 0.1 + 0.4 * math.exp(-episode/100)
        time.sleep(0.01)
        
        # 10 epizódonként szinkronizálás
        if episode % 10 == 0:
            with ai_trainer.q_table_lock:
                ai_trainer.q_table.update(local_trainer.q_table)
            print(f"Epizód: {episode} | Állapotok: {len(ai_trainer.q_table)}")
    
    if event.key == pygame.K_F2:
        ai_trainer.save_q_table()
        print("✅ Kézi mentés kész!")

    local_trainer.save_q_table()
    print("Tanulás leállt")

# Fő játék indítása
if __name__ == "__main__":
    import threading
    trainer_thread = threading.Thread(target=accelerated_training, daemon=True)
    trainer_thread.do_run = True  # Új flag a szál vezérléséhez
    trainer_thread.start()


running = True
while running:
    draw_field()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F1:
                    trainer_thread.do_run = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            if game_state == "menu":
                if event.key == pygame.K_1:
                    game_mode = "single"
                    game_state = "skin_select_single"
                elif event.key == pygame.K_2:
                    game_mode = "multi"
                    game_state = "skin_select_multi"
                elif event.key == pygame.K_h:
                    game_state = "history"

            elif game_state.startswith("skin_select"):
                if event.key == pygame.K_LEFT:
                    if game_state == "skin_select_single":
                        selected_skin_p1 = (selected_skin_p1 - 1) % 8
                    else:
                        if skin_selection_phase == 1:
                            selected_skin_p1 = (selected_skin_p1 - 1) % 8
                        else:
                            selected_skin_p2 = (selected_skin_p2 - 1) % 8
                elif event.key == pygame.K_RIGHT:
                    if game_state == "skin_select_single":
                        selected_skin_p1 = (selected_skin_p1 + 1) % 8
                    else:
                        if skin_selection_phase == 1:
                            selected_skin_p1 = (selected_skin_p1 + 1) % 8
                        else:
                            selected_skin_p2 = (selected_skin_p2 + 1) % 8
                elif event.key == pygame.K_RETURN:
                    if game_state == "skin_select_multi":
                        if skin_selection_phase == 1:
                            skin_selection_phase = 2
                        else:
                            game_state = "running"
                            start_ticks = pygame.time.get_ticks()
                            if game_mode == "single":
                                ai_skin_index = random.randint(0, 7)
                            reset_positions()
                    else:
                        game_state = "running"
                        start_ticks = pygame.time.get_ticks()
                        if game_mode == "single":
                            ai_skin_index = random.randint(0, 7)
                        reset_positions()
                elif event.key == pygame.K_q:
                    game_state = "menu"
                    skin_selection_phase = 1

            elif game_state == "running":
                if event.key == pygame.K_p:
                    paused = not paused
                elif event.key == pygame.K_q:
                    game_state = "menu"
                    score_left = score_right = 0
                    reset_positions()

            elif game_state == "game_over":
                if event.key == pygame.K_RETURN:
                    if match_name_input != "":
                        cursor.execute("INSERT INTO matches (name, score_left, score_right) VALUES (?, ?, ?)",
                                       (match_name_input, score_left, score_right))
                        conn.commit()
                        match_name_input = ""
                        game_state = "menu"
                        score_left = score_right = 0
                        reset_positions()
                elif event.key == pygame.K_BACKSPACE:
                    match_name_input = match_name_input[:-1]
                else:
                    match_name_input += event.unicode

            elif game_state == "history":
                if event.key == pygame.K_q:
                    game_state = "menu"

    if game_state == "menu":
        menu_text = font.render("1-Egyjátékos | 2-Kétjátékos | H - Meccstörténet", True, WHITE)
        instruction_text = small_font.render("ESC - Kilépés | Q - Vissza", True, WHITE)
        screen.blit(menu_text, (WIDTH//2 - menu_text.get_width()//2, HEIGHT//2 - 40))
        screen.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, HEIGHT//2 + 20))

    elif game_state.startswith("skin_select"):
        title_text = font.render("Válassz skint (Bal/Jobbra nyilak)", True, WHITE)
        instruction_text = small_font.render("Enter - Kiválasztás | Q - Vissza", True, WHITE)
        screen.blit(title_text, (WIDTH//2 - title_text.get_width()//2, 20))
        screen.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, 70))
        
        if game_state == "skin_select_multi":
            phase_text = small_font.render(f"Játékos {skin_selection_phase} választ", True, WHITE)
            screen.blit(phase_text, (WIDTH//2 - phase_text.get_width()//2, 120))
        
        x_pos = WIDTH//2 - 200
        for i in range(8):
            if (game_state == "skin_select_single" and i == selected_skin_p1) or \
               (game_state == "skin_select_multi" and skin_selection_phase == 1 and i == selected_skin_p1) or \
               (game_state == "skin_select_multi" and skin_selection_phase == 2 and i == selected_skin_p2):
                pygame.draw.rect(screen, YELLOW, (x_pos-5, 150-5, 50, 50), 3)
            screen.blit(player_skins[i], (x_pos, 150))
            x_pos += 60

    elif game_state == "running" and not paused:
        keys = pygame.key.get_pressed()
        if player1:
            player1.move(keys, pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s)
        
        # AI mozgáskezelés
        if game_mode == "single" and player2 and ball:
            # Előző állapotok mentése
            player2.kicking = False
            prev_score_left = score_left
            prev_score_right = score_right
            # Állapot és akció kiválasztása
            current_state = ai_trainer.get_state(ball.rect.center, player2.rect.center, ball.vel_x)
            action = ai_trainer.choose_action(current_state)
            
            # Akció végrehajtása
            if action == "left":
                player2.vel_x = -5
                player2.rect.x -= 5
            elif action == "right":
                player2.vel_x = 5
                player2.rect.x += 5
            elif action == "jump" and player2.on_ground:
                player2.vel_y = JUMP_STRENGTH
                player2.on_ground = False
            elif action == "kick":  # Új kick kezelés
                player2.kicking = True
                # Automatikus rúgás detekció a labda közelében
                if player2.rect.colliderect(ball.rect.inflate(30, 30)):
                    direction = 1 if player2.rect.centerx < ball.rect.centerx else -1
                    ball.vel_x = direction * 10 + player2.vel_x * 0.7
                    ball.vel_y = -12
        elif game_mode == "multi" and player2:
            player2.move(keys, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN)

        # Fizikai mozgások
        if player1:
            player1.apply_gravity()
        if player2:
            player2.apply_gravity()
        if ball:
            ball.move()
            if player1:
                ball.check_collision(player1)
            if player2:
                ball.check_collision(player2)

        if player1 and player2:
            player1.check_collision(player2)
            player2.check_collision(player1)
            

        if player1:
            player1.draw()
        if player2:
            player2.draw()
        if ball:
            ball.draw()
            
        draw_score()

        # Q-tábla frissítése AI-nak
        if game_mode == "single" and player2 and ball:
            current_state = ai_trainer.get_state(
            ball.rect.center, 
            player2.rect.center,
            ball.vel_x  # Labda sebesség átadása
        )
            new_score_left = score_left
            new_score_right = score_right
            goal_event = None
            if new_score_right > prev_score_right:
                goal_event = "goal_for"
            elif new_score_left > prev_score_left:
                goal_event = "own_goal"
            
            prev_score_diff = prev_score_right - prev_score_left
            new_score_diff = new_score_right - new_score_left
            reward = ai_trainer.calculate_reward(new_score_diff, prev_score_diff, goal_event)
            new_state = ai_trainer.get_state(ball.rect.center, player2.rect.center, ball.vel_x)
            ai_trainer.update_q_table(current_state, action, reward, new_state)
            ai_trainer.log_training_data(current_state, action, reward, new_state)
            reward_history.append(reward)  # Új

        # Időzítő kezelése
        if start_ticks:
            elapsed_time = (pygame.time.get_ticks() - start_ticks) / 1000
            timer_text = small_font.render(f"Idő: {int(match_duration - elapsed_time)}", True, WHITE)
            screen.blit(timer_text, (10, 10))
            if elapsed_time >= match_duration:
                game_state = "game_over"

    elif paused:
        pause_text = font.render("SZÜNET", True, YELLOW)
        screen.blit(pause_text, (WIDTH//2 - pause_text.get_width()//2, HEIGHT//2))

    elif game_state == "game_over":
        over_text = font.render("Meccs vége!", True, YELLOW)
        input_prompt = small_font.render("Írd be a meccs nevét és nyomd meg az ENTER-t:", True, WHITE)
        name_surface = small_font.render(match_name_input, True, WHITE)
        screen.blit(over_text, (WIDTH//2 - over_text.get_width()//2, HEIGHT//2 - 60))
        screen.blit(input_prompt, (WIDTH//2 - input_prompt.get_width()//2, HEIGHT//2 - 20))
        screen.blit(name_surface, (WIDTH//2 - name_surface.get_width()//2, HEIGHT//2 + 20))
        ai_won = score_right > score_left
        ai_trainer.update_after_match(ai_won)
        
        # Statisztikák frissítése
        if ai_won:
            ai_wins += 1
        else:
            human_wins += 1

    elif game_state == "history":
        history_title = font.render("Meccstörténet", True, WHITE)
        instruction_text = small_font.render("Q - Vissza", True, WHITE)
        screen.blit(history_title, (WIDTH//2 - history_title.get_width()//2, 10))
        screen.blit(instruction_text, (WIDTH//2 - instruction_text.get_width()//2, 50))
        
        cursor.execute("SELECT name, score_left, score_right, timestamp FROM matches ORDER BY id DESC")
        matches = cursor.fetchall()
        y_offset = 100
        for match in matches:
            match_str = f"{match[3]} - {match[0]}: {match[1]}:{match[2]}"
            match_text = small_font.render(match_str, True, WHITE)
            screen.blit(match_text, (50, y_offset))
            y_offset += 30
            if y_offset > HEIGHT - 30:
                break

    def print_ai_stats():
        total_actions = len(ai_trainer.q_table)
        unique_states = len({k[0] for k in ai_trainer.q_table.keys()})
        win_rate = (ai_wins / (ai_wins + human_wins)) * 100 if (ai_wins + human_wins) > 0 else 0
        
        print(f"\nAI Statisztikák:")
        print(f"- Tanult állapotok: {unique_states}")
        print(f"- Tanult akciók: {total_actions}")
        print(f"- Győzelmi arány: {win_rate:.1f}%")
        print(f"- Aktuális epsilon: {ai_trainer.epsilon:.2f}")
        print(f"- Utolsó 10 reward átlag: {sum(reward_history[-10:])/10 if len(reward_history)>=10 else 0:.1f}")
        print(f"- Win streak: {ai_trainer.win_streak}\n")

        # A játékciklusban hívni minden 10. meccs után
        if (ai_wins + human_wins) % 10 == 0:
            print_ai_stats()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
ai_trainer.save_q_table()
conn.close()

