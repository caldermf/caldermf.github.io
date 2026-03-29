from __future__ import annotations

import itertools
import random
import unittest

from burnside_sampler.pure_python import (
    PrimeFieldBurnsideSampler,
    mat_inv,
    mat_mul,
    partitions,
    right_steinberg_cell_key,
    rsk_insertion_tableau,
)
from tests.helpers import (
    all_complete_flags,
    is_stable_complete_flag,
    jordan_block_matrix,
    quotient_action_matches,
    random_general_unipotent_matrix,
)


class PurePythonCorrectnessTests(unittest.TestCase):
    def test_rsk_insertion_tableau_matches_known_examples(self) -> None:
        self.assertEqual(rsk_insertion_tableau((1, 2, 3)), ((1, 2, 3),))
        self.assertEqual(rsk_insertion_tableau((3, 2, 1)), ((1,), (2,), (3,)))
        self.assertEqual(rsk_insertion_tableau((2, 1, 3)), ((1, 3), (2,)))
        self.assertEqual(right_steinberg_cell_key((2, 1, 3)), "1,3|2")

    def test_rsk_right_cell_partition_is_constant_on_inverse_pairs(self) -> None:
        # For permutations in S_n, w and w^{-1} have swapped P/Q tableaux and therefore
        # the same Young shape. This guards the insertion implementation against drift.
        for n in range(1, 7):
            for permutation in itertools.permutations(range(1, n + 1)):
                inverse = tuple(
                    next(index + 1 for index, value in enumerate(permutation) if value == target)
                    for target in range(1, n + 1)
                )
                with self.subTest(n=n, permutation=permutation):
                    shape = tuple(len(row) for row in rsk_insertion_tableau(permutation))
                    inverse_shape = tuple(len(row) for row in rsk_insertion_tableau(inverse))
                    self.assertEqual(shape, inverse_shape)

    def test_green_polynomial_matches_bruteforce_flag_counts(self) -> None:
        for q in (2, 3):
            sampler = PrimeFieldBurnsideSampler(q)
            for n in range(1, 5):
                flags = all_complete_flags(n, q)
                for partition in partitions(n):
                    with self.subTest(q=q, partition=partition):
                        jordan = jordan_block_matrix(partition, q)
                        brute_force = sum(
                            1
                            for flag in flags
                            if is_stable_complete_flag(jordan, flag, q)
                        )
                        self.assertEqual(
                            sampler.green_polynomial_value(partition),
                            brute_force,
                        )

    def test_jordan_form_reconstructs_general_unipotent_matrices(self) -> None:
        for q in (2, 3, 5):
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(12345 + q)
            for n in range(1, 6):
                for partition in partitions(n):
                    for _ in range(3):
                        matrix = random_general_unipotent_matrix(partition, q, rng)
                        jordan, change_of_basis, found_partition = sampler.jordan_form(matrix)
                        with self.subTest(q=q, partition=partition, matrix=matrix):
                            self.assertEqual(found_partition, partition)
                            reconstructed = mat_mul(
                                mat_mul(change_of_basis, jordan, q),
                                mat_inv(change_of_basis, q),
                                q,
                            )
                            self.assertEqual(reconstructed, matrix)

    def test_quotient_representation_respects_action(self) -> None:
        for q in (2, 3, 5):
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(20260329 + q)
            for n in range(2, 6):
                start = tuple(range(1, n + 1))
                for _ in range(20):
                    matrix = sampler.random_stabilizer_element(start, rng)
                    vector = sampler.first_vector_sample(matrix, rng)
                    quotient, basis = sampler.quotient_representation(matrix, vector)
                    with self.subTest(q=q, n=n, matrix=matrix, vector=vector):
                        self.assertTrue(quotient_action_matches(matrix, quotient, basis, q))

    def test_sampled_flags_are_complete_and_stable(self) -> None:
        for q in (2, 3, 5):
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(99 + q)
            for n in range(2, 6):
                start = tuple(range(1, n + 1))
                for _ in range(30):
                    matrix = sampler.random_stabilizer_element(start, rng)
                    flag = sampler.springer_sample_flag(matrix, rng)
                    with self.subTest(q=q, n=n, matrix=matrix):
                        self.assertEqual(len(flag), n)
                        self.assertTrue(is_stable_complete_flag(matrix, flag, q))

    def test_next_step_returns_a_permutation(self) -> None:
        for q in (2, 3, 5):
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(777 + q)
            for n in range(1, 7):
                current = tuple(range(1, n + 1))
                for _ in range(20):
                    current = sampler.next_step(current, rng)
                    with self.subTest(q=q, n=n, current=current):
                        self.assertEqual(sorted(current), list(range(1, n + 1)))


if __name__ == "__main__":
    unittest.main()
