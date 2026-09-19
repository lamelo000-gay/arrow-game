# -*- coding: utf-8 -*-
"""
tools/make_screenshots.py —— 离屏渲染游戏截图与通关演示 GIF

原理：使用 SDL dummy 视频驱动离屏渲染，驱动 GameApp 的 update/draw 流程，
抓取开始界面、游戏界面、碰撞反馈、通关、失败等截图，并按关卡最优解模拟
点击，生成一张第一关通关演示 GIF。
输出到项目根目录 screenshots/ 下。

运行：python tools/make_screenshots.py
"""

import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"     # 必须在 import pygame 之前设置
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pygame

from main import GameApp, WIDTH, HEIGHT, FPS, CELL
from game_logic import find_solution

OUT_DIR = os.path.join(ROOT, "screenshots")


def save(app, name):
    pygame.image.save(app.screen, os.path.join(OUT_DIR, name))
    print("saved", name)


def cell_center(app, row, col):
    x0, y0, _, _ = app.board_rect()
    return x0 + col * CELL + CELL // 2, y0 + row * CELL + CELL // 2


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    app = GameApp(screen)

    # 1. 开始界面
    app.state = "start"
    app.draw()
    save(app, "start.png")

    # 2. 各关卡游戏界面
    for i in range(3):
        app.start_level(i)
        app.draw()
        save(app, "game_level{}.png".format(i + 1))

    # 3. 碰撞反馈：第一关点击被 (3,2,↑) 阻挡的 (3,0,→)
    app.start_level(0)
    x, y = cell_center(app, 3, 0)
    app.click_board((x, y))
    app.update(0.05)
    app.draw()
    save(app, "collision.png")

    # 4. 通关界面：按最优解消除第一关全部箭头
    solution = find_solution(app.session.board)
    for row, col, _ in solution:
        x, y = cell_center(app, row, col)
        app.click_board((x, y))
    for _ in range(150):                    # 等待飞出动画结束并弹出通关界面
        app.update(1 / FPS)
        if app.state == "win":
            break
    app.draw()
    save(app, "win.png")

    # 5. 失败界面：只剩 1 次失误时点击被阻挡的箭头
    app.start_level(0)
    app.session.mistakes = 1
    x, y = cell_center(app, 3, 0)
    app.click_board((x, y))
    for _ in range(150):
        app.update(1 / FPS)
        if app.state == "lose":
            break
    app.draw()
    save(app, "lose.png")

    # 6. 第一关通关演示 GIF（含开始界面与碰撞演示）
    import PIL.Image
    frames = []

    def snap():
        small = pygame.transform.smoothscale(app.screen, (WIDTH // 2, HEIGHT // 2))
        raw = pygame.image.tostring(small, "RGB")
        frames.append(PIL.Image.frombytes("RGB", (WIDTH // 2, HEIGHT // 2), raw))

    app.state = "start"
    app.draw()
    snap()
    app.start_level(0)
    for _ in range(6):
        app.update(1 / FPS)
        app.draw()
        snap()
    # 先演示一次碰撞
    x, y = cell_center(app, 3, 0)
    app.click_board((x, y))
    for _ in range(14):
        app.update(1 / FPS)
        app.draw()
        snap()
    # 再按最优解消除
    for row, col, _ in find_solution(app.session.board):
        x, y = cell_center(app, row, col)
        app.click_board((x, y))
        for _ in range(9):
            app.update(1 / FPS)
            app.draw()
            snap()
    for _ in range(90):
        app.update(1 / FPS)
        app.draw()
        snap()
    frames[0].save(os.path.join(OUT_DIR, "demo.gif"), save_all=True,
                   append_images=frames[1:], duration=55, loop=0)
    print("saved demo.gif ({} frames)".format(len(frames)))

    pygame.quit()


if __name__ == "__main__":
    main()
