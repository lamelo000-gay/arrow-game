# -*- coding: utf-8 -*-
"""
tests.py —— “一箭又一箭”自动化测试（对应作业测试用例 T01~T06）

运行方式：python tests.py
不依赖 pygame，只测试纯逻辑模块 game_logic 与关卡数据 levels。
"""

import unittest

from game_logic import Arrow, Board, LevelSession, clone_board, find_solution
from levels import LEVELS


class TestPathDetection(unittest.TestCase):
    """箭头与路径判断：四个方向、边界处理。"""

    def test_four_directions_blocked(self):
        """四个方向均能正确判断阻挡。"""
        # 上：目标 (1,1,↑)，上方 (0,1) 有箭头 → 阻挡
        b = Board(3, 3, [(1, 1, 0), (0, 1, 1)])
        self.assertTrue(b.is_blocked(b.arrow_at(1, 1)))
        # 下：目标 (1,1,↓)，下方 (2,1) 有箭头 → 阻挡
        b = Board(3, 3, [(1, 1, 1), (2, 1, 1)])
        self.assertTrue(b.is_blocked(b.arrow_at(1, 1)))
        # 左：目标 (1,1,←)，左侧 (1,0) 有箭头 → 阻挡
        b = Board(3, 3, [(1, 1, 2), (1, 0, 1)])
        self.assertTrue(b.is_blocked(b.arrow_at(1, 1)))
        # 右：目标 (1,1,→)，右侧 (1,2) 有箭头 → 阻挡
        b = Board(3, 3, [(1, 1, 3), (1, 2, 1)])
        self.assertTrue(b.is_blocked(b.arrow_at(1, 1)))
        # 同一行/列且中间隔着空格，仍应判定为阻挡
        b = Board(1, 4, [(0, 0, 3), (0, 2, 1)])
        self.assertTrue(b.is_blocked(b.arrow_at(0, 0)))

    def test_four_directions_clear(self):
        """四个方向前方无箭头 → 畅通。"""
        b = Board(3, 3, [(1, 1, 0), (0, 2, 3)])
        self.assertFalse(b.is_blocked(b.arrow_at(1, 1)))
        b = Board(3, 3, [(1, 1, 1), (2, 2, 3)])
        self.assertFalse(b.is_blocked(b.arrow_at(1, 1)))
        b = Board(3, 3, [(1, 1, 2), (1, 2, 3)])
        self.assertFalse(b.is_blocked(b.arrow_at(1, 1)))
        b = Board(3, 3, [(1, 1, 3), (1, 0, 2)])
        self.assertFalse(b.is_blocked(b.arrow_at(1, 1)))

    def test_edge_arrow_out_of_bounds(self):
        """位于边缘且朝向棋盘外的箭头：畅通、可消除、不发生越界。"""
        b = Board(3, 3, [(0, 1, 0), (1, 0, 2), (2, 1, 1), (1, 2, 3)])
        for r, c, d in [(0, 1, 0), (1, 0, 2), (2, 1, 1), (1, 2, 3)]:
            a = b.arrow_at(r, c)
            self.assertFalse(b.is_blocked(a), "({},{}) 边缘朝外箭头应畅通".format(r, c))
            b.remove(a)
            self.assertIsNone(b.arrow_at(r, c))
        self.assertTrue(b.is_solved())


class TestT01T02T03(unittest.TestCase):
    """对应测试用例 T01 / T02 / T03。"""

    def test_T01_click_unblocked_arrow_flys_out(self):
        """T01 点击前方无阻挡的箭头 → 箭头飞出棋盘并消失。"""
        session = LevelSession(LEVELS[0])
        # 第一关 (0,2,→)：右侧无箭头，畅通
        result, arrow = session.click(0, 2)
        self.assertEqual(result, "fly")
        self.assertIsNone(session.board.arrow_at(0, 2))
        self.assertEqual(session.board.remaining(), len(LEVELS[0]["arrows"]) - 1)

    def test_T02_blocked_arrow_not_removed_mistake_decrement(self):
        """T02 点击前方有阻挡的箭头 → 箭头不消失，失误次数减 1。"""
        session = LevelSession(LEVELS[0])
        before = session.mistakes
        # 第一关 (3,0,→)：右侧 (3,2,↑) 阻挡
        result, arrow = session.click(3, 0)
        self.assertEqual(result, "blocked")
        self.assertIsNotNone(session.board.arrow_at(3, 0))
        self.assertEqual(session.mistakes, before - 1)
        self.assertEqual(session.status, "playing")

    def test_T03_edge_arrow_clears_without_error(self):
        """T03 点击位于边缘且朝向棋盘外的箭头 → 正常消失，不发生越界错误。"""
        session = LevelSession(LEVELS[0])
        # 第一关 (1,0,↑)：朝上即棋盘边界
        result, arrow = session.click(1, 0)
        self.assertEqual(result, "fly")
        self.assertIsNone(session.board.arrow_at(1, 0))


class TestGameFlow(unittest.TestCase):
    """对应测试用例 T04 / T05 / T06。"""

    def test_T04_clear_all_arrows_wins_and_next_level(self):
        """T04 消除本关全部箭头 → 显示通关并进入下一关。"""
        for i, level in enumerate(LEVELS):
            session = LevelSession(level)
            solution = find_solution(session.board)
            self.assertIsNotNone(solution)
            for row, col, _ in solution:
                result, _ = session.click(row, col)
                self.assertEqual(result, "fly")
            self.assertEqual(session.status, "won")
            self.assertEqual(session.board.remaining(), 0)
            # 进入下一关：新会话初始状态为 playing
            if i + 1 < len(LEVELS):
                nxt = LevelSession(LEVELS[i + 1])
                self.assertEqual(nxt.status, "playing")
                self.assertEqual(nxt.board.remaining(), len(LEVELS[i + 1]["arrows"]))

    def test_T05_mistakes_exhausted_fail_and_restart(self):
        """T05 失误次数耗尽 → 显示失败并允许重新开始。"""
        # 构造一个不可解局（两个箭头互相阻挡），失误上限 1
        level = {"rows": 1, "cols": 3, "mistakes": 1,
                 "arrows": [(0, 0, 3), (0, 2, 2)]}   # → 与 ← 互阻
        self.assertIsNone(find_solution(Board(1, 3, level["arrows"])))
        session = LevelSession(level)
        result, _ = session.click(0, 0)
        self.assertEqual(result, "blocked")
        self.assertEqual(session.mistakes, 0)
        self.assertEqual(session.status, "lost")
        # 重新开始 → 状态、失误次数、箭头布局恢复
        session.reset()
        self.assertEqual(session.status, "playing")
        self.assertEqual(session.mistakes, 1)
        self.assertEqual(session.board.remaining(), 2)

    def test_T06_restart_restores_layout_and_mistakes(self):
        """T06 游戏进行中重新开始 → 箭头布局和失误次数恢复。"""
        session = LevelSession(LEVELS[1])
        # 第二关 (1,0,→) 被 (1,2,↓) 阻挡、(2,1,→) 被 (2,3,↑) 阻挡，先点错两次
        self.assertEqual(session.click(1, 0)[0], "blocked")
        self.assertEqual(session.click(2, 1)[0], "blocked")
        self.assertEqual(session.mistakes, session.max_mistakes - 2)
        session.reset()
        self.assertEqual(session.mistakes, session.max_mistakes)
        self.assertEqual(session.board.remaining(), len(LEVELS[1]["arrows"]))
        self.assertEqual(session.status, "playing")


class TestLevels(unittest.TestCase):
    """关卡数据质量校验。"""

    def test_all_levels_solvable(self):
        """每个关卡都应存在合法、可行的消除顺序。"""
        for i, level in enumerate(LEVELS, 1):
            board = Board(level["rows"], level["cols"], level["arrows"])
            solution = find_solution(board)
            self.assertIsNotNone(solution, "第 {} 关不可解！".format(i))
            self.assertEqual(len(solution), len(level["arrows"]),
                             "第 {} 关消除顺序长度与箭头数不一致".format(i))
            # 逐步重放，验证每一步点击时该箭头确实畅通
            b = clone_board(board)
            for row, col, d in solution:
                a = b.arrow_at(row, col)
                self.assertIsNotNone(a, "第 {} 关第 {} 步目标箭头不存在".format(i, (row, col)))
                self.assertFalse(b.is_blocked(a),
                                 "第 {} 关第 {} 步点击时箭头被阻挡".format(i, (row, col)))
                b.remove(a)
            self.assertEqual(b.remaining(), 0, "第 {} 关消除后仍有剩余".format(i))

    def test_levels_have_four_directions(self):
        """每个关卡都应包含上、下、左、右四种方向的箭头。"""
        for i, level in enumerate(LEVELS, 1):
            dirs = {d for _, _, d in level["arrows"]}
            self.assertEqual(dirs, {0, 1, 2, 3}, "第 {} 关缺少某方向箭头".format(i))


if __name__ == "__main__":
    unittest.main(verbosity=2)
