# -*- coding: utf-8 -*-
"""
game_logic.py —— “一箭又一箭”核心游戏逻辑（不依赖 pygame，便于单元测试）

方向约定：0=上(UP)，1=下(DOWN)，2=左(LEFT)，3=右(RIGHT)
箭头表示：每个箭头是一个 Arrow 对象，记录 (row, col, direction)。
棋盘表示：Board 同时维护箭头集合与二维网格 grid，可 O(1) 查询某格是否有箭头。
路径检测：沿箭头方向逐格前进直到棋盘边界，只要途中存在其他箭头即判定为“被阻挡”。
"""

UP, DOWN, LEFT, RIGHT = 0, 1, 2, 3

# 各方向的 (行增量, 列增量)
DIR_STEP = {
    UP: (-1, 0),
    DOWN: (1, 0),
    LEFT: (0, -1),
    RIGHT: (0, 1),
}

DIR_NAMES = {UP: "上", DOWN: "下", LEFT: "左", RIGHT: "右"}


class Arrow:
    """棋盘上的一个箭头：由 (row, col, direction) 唯一确定。"""

    __slots__ = ("row", "col", "direction")

    def __init__(self, row, col, direction):
        self.row = row
        self.col = col
        self.direction = direction

    def __eq__(self, other):
        return (isinstance(other, Arrow)
                and self.row == other.row
                and self.col == other.col
                and self.direction == other.direction)

    def __hash__(self):
        return hash((self.row, self.col, self.direction))

    def __repr__(self):
        return "Arrow(r={}, c={}, dir={})".format(
            self.row, self.col, DIR_NAMES[self.direction])


class Board:
    """棋盘：负责箭头的存放、路径检测与消除。"""

    def __init__(self, rows, cols, arrows):
        self.rows = rows
        self.cols = cols
        self.grid = [[None] * cols for _ in range(rows)]
        self.arrows = set()
        for row, col, direction in arrows:
            arrow = Arrow(row, col, direction)
            self.arrows.add(arrow)
            self.grid[row][col] = arrow

    def in_bounds(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols

    def arrow_at(self, row, col):
        """返回 (row, col) 处的箭头；越界或空格返回 None。"""
        if not self.in_bounds(row, col):
            return None
        return self.grid[row][col]

    def is_blocked(self, arrow):
        """
        路径检测核心：判断箭头“前方到棋盘边界之间”是否存在其他箭头。
        沿方向逐格前进，只要发现任一箭头即返回 True；走到边界外返回 False。
        """
        dr, dc = DIR_STEP[arrow.direction]
        row, col = arrow.row + dr, arrow.col + dc
        while self.in_bounds(row, col):
            if self.grid[row][col] is not None:
                return True          # 前方有箭头 → 被阻挡
            row += dr
            col += dc
        return False                 # 直到边界都没有箭头 → 畅通

    def path_cells(self, arrow):
        """返回箭头前方到边界之间所有空格坐标（供飞出动画计算路径长度）。"""
        cells = []
        dr, dc = DIR_STEP[arrow.direction]
        row, col = arrow.row + dr, arrow.col + dc
        while self.in_bounds(row, col):
            cells.append((row, col))
            row += dr
            col += dc
        return cells

    def remove(self, arrow):
        """把箭头从棋盘上移除。"""
        if arrow in self.arrows:
            self.arrows.discard(arrow)
            self.grid[arrow.row][arrow.col] = None

    def remaining(self):
        return len(self.arrows)

    def is_solved(self):
        return len(self.arrows) == 0


def clone_board(board):
    """深拷贝一个棋盘（供求解器使用，不影响原棋盘）。"""
    arrows = [(a.row, a.col, a.direction) for a in board.arrows]
    return Board(board.rows, board.cols, arrows)


def find_solution(board):
    """
    用贪心法求一个可行的消除顺序。

    原理：消除一个箭头只会清空其路径、绝不会新增阻挡，因此“能消就消”不会破坏
    可解性；若某时刻没有任何箭头可消却仍有剩余箭头，则该局无解。
    返回：[(row, col, direction), ...] 的消除顺序；无解返回 None。
    """
    b = clone_board(board)
    order = []
    while b.arrows:
        removable = [a for a in b.arrows if not b.is_blocked(a)]
        if not removable:
            return None
        first = removable[0]
        b.remove(first)
        order.append((first.row, first.col, first.direction))
    return order


class LevelSession:
    """单关会话：管理棋盘、失误次数与 进行中/通关/失败 状态。"""

    def __init__(self, level):
        self.level_data = level
        self.rows = level["rows"]
        self.cols = level["cols"]
        self.board = Board(level["rows"], level["cols"], level["arrows"])
        self.max_mistakes = level.get("mistakes", 5)
        self.mistakes = self.max_mistakes
        self.status = "playing"      # playing / won / lost

    def click(self, row, col):
        """
        点击 (row, col) 处的箭头。
        返回 (result, arrow)：
          ("fly", arrow)    箭头畅通，已飞出并消除
          ("blocked", arrow) 箭头被阻挡，失误次数 -1
          ("none", None)    点击空白处，或游戏已结束
        """
        if self.status != "playing":
            return ("none", None)
        arrow = self.board.arrow_at(row, col)
        if arrow is None:
            return ("none", None)
        if self.board.is_blocked(arrow):
            self.mistakes -= 1
            if self.mistakes <= 0:
                self.status = "lost"
            return ("blocked", arrow)
        # 前方畅通 → 消除该箭头
        self.board.remove(arrow)
        if self.board.is_solved():
            self.status = "won"
        return ("fly", arrow)

    def reset(self):
        """重新开始本关：恢复初始布局与失误次数。"""
        self.__init__(self.level_data)
