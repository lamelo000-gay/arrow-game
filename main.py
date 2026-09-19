# -*- coding: utf-8 -*-
"""
main.py —— “一箭又一箭”小游戏主程序（pygame 图形界面）

运行方式：python main.py

界面流程：
    开始界面 → 游戏界面 →（通关界面 / 失败界面）→ 下一关或重新开始
界面包含：当前关卡、游戏棋盘、剩余箭头数量、剩余失误次数、重新开始按钮。
"""

import math
import sys

import pygame

from game_logic import DIR_STEP, LevelSession, UP, DOWN, LEFT, RIGHT
from levels import LEVELS

# ---------- 窗口与配色 ----------
WIDTH, HEIGHT = 880, 700
FPS = 60
CELL = 84                       # 棋盘格子边长（像素）

BG_COLOR = (245, 241, 232)      # 页面背景（米白）
HUD_BG = (236, 230, 218)
GRID_COLOR = (208, 197, 176)    # 网格线
CELL_A = (252, 249, 242)        # 棋盘格子（浅）
CELL_B = (246, 241, 231)        # 棋盘格子（深）
HUD_COLOR = (52, 58, 64)        # 文字（深灰）
ACCENT = (47, 111, 237)         # 箭头主色（蓝）
ACCENT_DARK = (27, 70, 160)
RED = (222, 66, 66)             # 碰撞 / 失误提示色
WHITE = (255, 255, 255)
OVERLAY = (0, 0, 0, 160)
HOVER = (255, 220, 130)


def load_font(size):
    """优先加载支持中文的系统字体，找不到时退回默认字体。"""
    for name in ("microsoftyahei", "microsoftyaheiui", "simhei", "simsun", "dengxian"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def draw_arrow(surface, x, y, direction, size, color=ACCENT, outline=WHITE):
    """在中心点 (x, y) 绘制一个指向 direction 的箭头（箭头杆 + 箭头）。"""
    s = size / 2.0
    if direction == UP:
        head = [(x, y - s), (x - s * 0.55, y - s * 0.05), (x + s * 0.55, y - s * 0.05)]
        shaft = pygame.Rect(int(x - s * 0.18), int(y - s * 0.1), int(s * 0.36), int(s * 0.55))
    elif direction == DOWN:
        head = [(x, y + s), (x - s * 0.55, y + s * 0.05), (x + s * 0.55, y + s * 0.05)]
        shaft = pygame.Rect(int(x - s * 0.18), int(y - s * 0.45), int(s * 0.36), int(s * 0.55))
    elif direction == LEFT:
        head = [(x - s, y), (x - s * 0.05, y - s * 0.55), (x - s * 0.05, y + s * 0.55)]
        shaft = pygame.Rect(int(x - s * 0.1), int(y - s * 0.18), int(s * 0.55), int(s * 0.36))
    else:  # RIGHT
        head = [(x + s, y), (x + s * 0.05, y - s * 0.55), (x + s * 0.05, y + s * 0.55)]
        shaft = pygame.Rect(int(x - s * 0.45), int(y - s * 0.18), int(s * 0.55), int(s * 0.36))
    pygame.draw.polygon(surface, color, head)
    pygame.draw.rect(surface, color, shaft)
    pygame.draw.polygon(surface, outline, head, 2)
    pygame.draw.rect(surface, outline, shaft, 2)


class Button:
    """圆角按钮。"""

    def __init__(self, text, center, size=(210, 56), font_size=28,
                 color=ACCENT, hover=(69, 130, 245), text_color=WHITE):
        self.text = text
        self.rect = pygame.Rect(0, 0, *size)
        self.rect.center = center
        self.font = load_font(font_size)
        self.color = color
        self.hover = hover
        self.text_color = text_color

    def draw(self, surface, mouse_pos):
        shadow = self.rect.move(0, 4)
        pygame.draw.rect(surface, (30, 62, 130), shadow, border_radius=14)
        color = self.hover if self.rect.collidepoint(mouse_pos) else self.color
        pygame.draw.rect(surface, color, self.rect, border_radius=14)
        text = self.font.render(self.text, True, self.text_color)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class FlyingArrow:
    """飞出动画：箭头沿其方向加速飞离棋盘并淡出。"""

    def __init__(self, arrow, start_px, distance_px, duration=0.38):
        self.arrow = arrow
        self.x, self.y = start_px
        self.distance = distance_px
        self.duration = duration
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def done(self):
        return self.time >= self.duration

    def position(self):
        t = min(self.time / self.duration, 1.0)
        eased = t * t                     # 加速飞出
        dx, dy = DIR_STEP[self.arrow.direction]
        return (self.x + dx * self.distance * eased,
                self.y + dy * self.distance * eased)

    def alpha(self):
        t = min(self.time / self.duration, 1.0)
        return max(0, int(255 * (1 - max(0.0, (t - 0.5) / 0.5))))


class CollideFeedback:
    """碰撞反馈：箭头沿方向左右/上下晃动、变红闪烁，并显示“被阻挡！”文字。"""

    def __init__(self, arrow, cell_center, duration=0.55):
        self.arrow = arrow
        self.x, self.y = cell_center
        self.duration = duration
        self.time = 0.0

    def update(self, dt):
        self.time += dt

    def done(self):
        return self.time >= self.duration

    def offset(self):
        t = min(self.time / self.duration, 1.0)
        amp = 9 * max(0.0, 1.0 - t) * math.sin(t * math.pi * 10)
        dr, dc = DIR_STEP[self.arrow.direction]
        return dc * amp, dr * amp

    def flash_red(self):
        return self.time < 0.35 * self.duration


class GameApp:
    """游戏应用：管理界面状态、事件与渲染。"""

    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font = load_font(28)
        self.font_small = load_font(20)
        self.font_title = load_font(56)
        self.mouse_pos = (0, 0)

        # 界面状态
        self.state = "start"            # start / playing / win / lose
        self.level_index = 0
        self.session = None
        self.flying = []                # 飞出动画列表
        self.collides = []              # 碰撞反馈列表
        self.pending_timer = 0.0        # 通关 / 失败界面延迟计时

        # 按钮
        cx, cy = WIDTH // 2, HEIGHT // 2
        self.btn_start = Button("开始游戏", (cx, cy + 90))
        self.btn_next = Button("进入下一关", (cx, cy + 95))
        self.btn_again = Button("再玩一次", (cx, cy + 95))
        self.btn_retry = Button("重新开始", (cx, cy + 95))
        self.btn_menu = Button("返回主页", (cx, cy + 175), size=(210, 48), font_size=24)
        self.btn_restart_game = Button("重新开始", (WIDTH - 120, 48), size=(150, 44), font_size=22)
        self.btn_back_menu = Button("主页", (WIDTH - 292, 48), size=(100, 44), font_size=22)

    # ---------- 关卡控制 ----------
    def start_level(self, index):
        self.level_index = index
        self.session = LevelSession(LEVELS[index])
        self.flying.clear()
        self.collides.clear()
        self.pending_timer = 0.0
        self.state = "playing"

    # ---------- 事件处理 ----------
    def handle_click(self, pos):
        if self.state == "start":
            if self.btn_start.is_clicked(pos):
                self.start_level(0)
        elif self.state == "playing":
            if self.btn_restart_game.is_clicked(pos):
                self.start_level(self.level_index)
            elif self.btn_back_menu.is_clicked(pos):
                self.state = "start"
            else:
                self.click_board(pos)
        elif self.state == "win":
            last = self.level_index == len(LEVELS) - 1
            main_btn = self.btn_again if last else self.btn_next
            if main_btn.is_clicked(pos):
                self.start_level(0 if last else self.level_index + 1)
            elif self.btn_menu.is_clicked(pos):
                self.state = "start"
        elif self.state == "lose":
            if self.btn_retry.is_clicked(pos):
                self.start_level(self.level_index)
            elif self.btn_menu.is_clicked(pos):
                self.state = "start"

    def click_board(self, pos):
        x0, y0, _, _ = self.board_rect()
        col = (pos[0] - x0) // CELL
        row = (pos[1] - y0) // CELL
        result, arrow = self.session.click(row, col)
        if result == "fly":
            self._spawn_flying(arrow)
            if self.session.status == "won":
                self.pending_timer = 0.7
        elif result == "blocked":
            self._spawn_collision(arrow)
            if self.session.status == "lost":
                self.pending_timer = 0.6

    def _spawn_flying(self, arrow):
        x0, y0, _, _ = self.board_rect()
        cx = x0 + arrow.col * CELL + CELL // 2
        cy = y0 + arrow.row * CELL + CELL // 2
        rows, cols = self.session.rows, self.session.cols
        dr, dc = DIR_STEP[arrow.direction]
        if dc == 1:
            dist = (cols - arrow.col) * CELL
        elif dc == -1:
            dist = (arrow.col + 1) * CELL
        elif dr == -1:
            dist = (arrow.row + 1) * CELL
        else:
            dist = (rows - arrow.row) * CELL
        self.flying.append(FlyingArrow(arrow, (cx, cy), dist))

    def _spawn_collision(self, arrow):
        x0, y0, _, _ = self.board_rect()
        cx = x0 + arrow.col * CELL + CELL // 2
        cy = y0 + arrow.row * CELL + CELL // 2
        self.collides.append(CollideFeedback(arrow, (cx, cy)))

    # ---------- 几何 ----------
    def board_rect(self):
        rows, cols = self.session.rows, self.session.cols
        bw, bh = cols * CELL, rows * CELL
        x0 = (WIDTH - bw) // 2
        y0 = 130 + (HEIGHT - 130 - bh) // 2
        return x0, y0, bw, bh

    # ---------- 主循环 ----------
    def update(self, dt):
        for f in self.flying[:]:
            f.update(dt)
            if f.done():
                self.flying.remove(f)
        for c in self.collides[:]:
            c.update(dt)
            if c.done():
                self.collides.remove(c)
        if self.state == "playing":
            if self.session.status == "won" and not self.flying:
                self.pending_timer -= dt
                if self.pending_timer <= 0:
                    self.state = "win"
            elif self.session.status == "lost" and not self.collides:
                self.pending_timer -= dt
                if self.pending_timer <= 0:
                    self.state = "lose"

    def draw(self):
        s = self.screen
        s.fill(BG_COLOR)
        if self.state == "start":
            self._draw_start()
        elif self.state == "playing":
            self._draw_game()
        elif self.state == "win":
            self._draw_game()
            self._draw_overlay("win")
        elif self.state == "lose":
            self._draw_game()
            self._draw_overlay("lose")

    # ---------- 开始界面 ----------
    def _draw_start(self):
        s = self.screen
        title = self.font_title.render("一箭又一箭", True, ACCENT_DARK)
        s.blit(title, title.get_rect(center=(WIDTH // 2, 150)))
        sub = self.font_small.render("点击箭头使其飞出棋盘；前方被阻挡时会消耗一次失误机会", True, HUD_COLOR)
        s.blit(sub, sub.get_rect(center=(WIDTH // 2, 205)))
        rules = [
            "· 棋盘中的箭头有 上 / 下 / 左 / 右 四种方向",
            "· 点击箭头：若其前方到棋盘边界没有其他箭头，即可飞出消除",
            "· 若前方有其他箭头，箭头会晃动变红提示碰撞，并消耗 1 次失误",
            "· 清除本关全部箭头即通关；失误次数耗尽则本关失败",
            "· 每关都有合理的消除顺序，注意先消除挡路的箭头！",
        ]
        y = 255
        for line in rules:
            text = self.font_small.render(line, True, HUD_COLOR)
            s.blit(text, text.get_rect(center=(WIDTH // 2, y)))
            y += 34
        # 示例小棋盘
        demo = [(0, 1, RIGHT), (1, 3, UP)]
        demo_x, demo_y, demo_size = 350, 430, 52
        for r in range(2):
            for c in range(4):
                rect = pygame.Rect(demo_x + c * demo_size, demo_y + r * demo_size, demo_size, demo_size)
                pygame.draw.rect(s, CELL_A if (r + c) % 2 == 0 else CELL_B, rect)
                pygame.draw.rect(s, GRID_COLOR, rect, 1)
        for r, c, d in demo:
            draw_arrow(s, demo_x + c * demo_size + demo_size // 2,
                       demo_y + r * demo_size + demo_size // 2, d, demo_size * 0.6)
        tip1 = self.font_small.render("↑ 朝上即边界，可点击飞出", True, HUD_COLOR)
        s.blit(tip1, tip1.get_rect(center=(620, 445)))
        self.btn_start.draw(s, self.mouse_pos)

    # ---------- 游戏界面 ----------
    def _draw_game(self):
        s = self.screen
        level = LEVELS[self.level_index]

        # 顶部 HUD
        pygame.draw.rect(s, HUD_BG, (0, 0, WIDTH, 96))
        pygame.draw.line(s, GRID_COLOR, (0, 96), (WIDTH, 96), 2)
        text1 = self.font.render("关卡：" + level["name"], True, HUD_COLOR)
        s.blit(text1, (26, 24))
        text2 = self.font.render("剩余箭头：{}".format(self.session.board.remaining()), True, HUD_COLOR)
        s.blit(text2, (26, 60))
        label = self.font.render("剩余失误：", True, HUD_COLOR)
        label_rect = label.get_rect(midleft=(WIDTH // 2 - 200, 60))
        s.blit(label, label_rect)
        for i in range(self.session.max_mistakes):
            self._draw_heart(s, (label_rect.right + 18 + i * 30, 62), i < self.session.mistakes)
        self.btn_restart_game.draw(s, self.mouse_pos)
        self.btn_back_menu.draw(s, self.mouse_pos)

        # 棋盘
        x0, y0, bw, bh = self.board_rect()
        pygame.draw.rect(s, (238, 231, 218), (x0 - 16, y0 - 16, bw + 32, bh + 32), border_radius=16)
        pygame.draw.rect(s, GRID_COLOR, (x0 - 16, y0 - 16, bw + 32, bh + 32), 2, border_radius=16)
        for r in range(self.session.rows):
            for c in range(self.session.cols):
                rect = pygame.Rect(x0 + c * CELL, y0 + r * CELL, CELL, CELL)
                pygame.draw.rect(s, CELL_A if (r + c) % 2 == 0 else CELL_B, rect)
                pygame.draw.rect(s, GRID_COLOR, rect, 1)

        # 悬停高亮
        hx, hy = self.mouse_pos
        hr, hc = (hy - y0) // CELL, (hx - x0) // CELL
        if self.session.board.in_bounds(hr, hc) and self.session.board.arrow_at(hr, hc):
            pygame.draw.rect(s, HOVER, (x0 + hc * CELL, y0 + hr * CELL, CELL, CELL), 3, border_radius=10)

        # 静止箭头（正在碰撞反馈的箭头由反馈层绘制）
        colliding = {id(c.arrow) for c in self.collides}
        for a in self.session.board.arrows:
            if id(a) in colliding:
                continue
            cx = x0 + a.col * CELL + CELL // 2
            cy = y0 + a.row * CELL + CELL // 2
            draw_arrow(s, cx, cy, a.direction, CELL * 0.6)

        # 碰撞反馈层
        for c in self.collides:
            cx = x0 + c.arrow.col * CELL + CELL // 2
            cy = y0 + c.arrow.row * CELL + CELL // 2
            dx, dy = c.offset()
            draw_arrow(s, cx + dx, cy + dy, c.arrow.direction, CELL * 0.6,
                       color=RED if c.flash_red() else ACCENT)
            if c.flash_red():
                tip = self.font_small.render("被阻挡！", True, RED)
                s.blit(tip, tip.get_rect(center=(cx, cy - CELL * 0.75)))

        # 飞出动画层
        for f in self.flying:
            px, py = f.position()
            draw_arrow(s, px, py, f.arrow.direction, CELL * 0.6)

    def _draw_heart(self, s, center, filled):
        x, y = center
        color = RED if filled else (198, 194, 186)
        pygame.draw.circle(s, color, (x - 8, y - 4), 9)
        pygame.draw.circle(s, color, (x + 8, y - 4), 9)
        pygame.draw.polygon(s, color, [(x - 16, y - 2), (x + 16, y - 2), (x, y + 14)])

    # ---------- 通关 / 失败界面 ----------
    def _draw_overlay(self, kind):
        s = self.screen
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill(OVERLAY)
        s.blit(overlay, (0, 0))

        panel = pygame.Rect(0, 0, 560, 380)
        panel.center = (WIDTH // 2, HEIGHT // 2 + 15)
        pygame.draw.rect(s, WHITE, panel, border_radius=20)
        pygame.draw.rect(s, GRID_COLOR, panel, 2, border_radius=20)

        if kind == "win":
            last = self.level_index == len(LEVELS) - 1
            title = "恭喜通关！" if not last else "恭喜完成全部关卡！"
            sub = "干得漂亮，准备进入下一关！" if not last else "你真棒，所有关卡都已通关！"
            main_btn = self.btn_again if last else self.btn_next
        else:
            title = "挑战失败"
            sub = "失误次数已用完，别灰心，再试一次吧！"
            main_btn = self.btn_retry

        t = self.font_title.render(title, True, ACCENT_DARK if kind == "win" else RED)
        s.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
        st = self.font_small.render(sub, True, HUD_COLOR)
        s.blit(st, st.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        main_btn.draw(s, self.mouse_pos)
        self.btn_menu.draw(s, self.mouse_pos)

    # ---------- 运行 ----------
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEMOTION:
                    self.mouse_pos = event.pos
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == "playing":
                            self.state = "start"
                        else:
                            running = False
            self.update(dt)
            self.draw()
            pygame.display.flip()
        pygame.quit()


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("一箭又一箭")
    app = GameApp(screen)
    if "--smoke-test" in sys.argv:
        # 冒烟测试：无人工交互，自动渲染 60 帧后退出
        app.start_level(0)
        for _ in range(60):
            app.update(1 / FPS)
            app.draw()
            pygame.display.flip()
        pygame.quit()
        return
    app.run()


if __name__ == "__main__":
    main()
