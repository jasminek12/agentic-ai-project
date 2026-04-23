"""Offline coding practice challenge bank and lightweight runner config."""

from __future__ import annotations

from typing import TypedDict


class CodingTest(TypedDict):
    input: object
    expected: object


class CodingChallenge(TypedDict):
    id: str
    title: str
    difficulty: str
    prompt: str
    function_name: str
    starter_code: str
    tests: list[CodingTest]
    hints: list[str]


CHALLENGES: list[CodingChallenge] = [
    {
        "id": "two_sum",
        "title": "Two Sum",
        "difficulty": "easy",
        "prompt": (
            "Given a list of integers `nums` and an integer `target`, return indices of the "
            "two numbers such that they add up to `target`. Assume exactly one valid answer."
        ),
        "function_name": "solve",
        "starter_code": (
            "def solve(nums, target):\n"
            "    # Return a list/tuple of two indices.\n"
            "    # Example: nums=[2,7,11,15], target=9 -> [0,1]\n"
            "    pass\n"
        ),
        "tests": [
            {"input": ([2, 7, 11, 15], 9), "expected": [0, 1]},
            {"input": ([3, 2, 4], 6), "expected": [1, 2]},
            {"input": ([3, 3], 6), "expected": [0, 1]},
        ],
        "hints": [
            "Think hash map: value -> index.",
            "At each index, compute complement = target - current.",
        ],
    },
    {
        "id": "valid_parentheses",
        "title": "Valid Parentheses",
        "difficulty": "easy",
        "prompt": (
            "Given a string containing just the characters '(', ')', '{', '}', '[' and ']', "
            "determine if the input string is valid."
        ),
        "function_name": "solve",
        "starter_code": (
            "def solve(s):\n"
            "    # Return True if s is valid, else False.\n"
            "    pass\n"
        ),
        "tests": [
            {"input": ("()",), "expected": True},
            {"input": ("()[]{}",), "expected": True},
            {"input": ("(]",), "expected": False},
            {"input": ("([{}])",), "expected": True},
        ],
        "hints": [
            "A stack handles nested structure cleanly.",
            "Map closing brackets to expected opening brackets.",
        ],
    },
    {
        "id": "max_subarray",
        "title": "Maximum Subarray",
        "difficulty": "medium",
        "prompt": (
            "Given an integer array `nums`, find the contiguous subarray with the largest sum "
            "and return its sum."
        ),
        "function_name": "solve",
        "starter_code": (
            "def solve(nums):\n"
            "    # Return the maximum possible subarray sum.\n"
            "    pass\n"
        ),
        "tests": [
            {"input": ([-2, 1, -3, 4, -1, 2, 1, -5, 4],), "expected": 6},
            {"input": ([1],), "expected": 1},
            {"input": ([5, 4, -1, 7, 8],), "expected": 23},
        ],
        "hints": [
            "Kadane's algorithm runs in O(n).",
            "Track best-so-far and current best ending at i.",
        ],
    },
]

