from __future__ import annotations

import itertools
import random
import unittest

from burnside_sampler.pure_python import PrimeFieldBurnsideSampler, partitions, rsk_insertion_tableau
from tests.helpers import random_general_unipotent_matrix

try:
    from sage.all import matrix, vector
    from sage.combinat.permutation import Permutation
    from burnside_sampler.oracle_sage import SageBurnsideOracle, sage_matrix_to_tuple, sage_vector_to_tuple

    HAVE_SAGE = True
except Exception:  # pragma: no cover - exercised only outside Sage.
    HAVE_SAGE = False


@unittest.skipUnless(HAVE_SAGE, "Sage is required for oracle-alignment tests.")
class OracleAlignmentTests(unittest.TestCase):
    def test_rsk_insertion_tableau_matches_sage(self) -> None:
        for n in range(1, 7):
            for permutation in itertools.permutations(range(1, n + 1)):
                sage_tableau, _ = Permutation(list(permutation)).robinson_schensted()
                with self.subTest(n=n, permutation=permutation):
                    self.assertEqual(
                        rsk_insertion_tableau(permutation),
                        tuple(tuple(int(value) for value in row) for row in sage_tableau),
                    )

    def test_green_values_and_smaller_distributions_match(self) -> None:
        for q in (2, 3, 5):
            oracle = SageBurnsideOracle(q)
            sampler = PrimeFieldBurnsideSampler(q)
            for n in range(1, 6):
                for partition in partitions(n):
                    with self.subTest(q=q, partition=partition):
                        self.assertEqual(
                            sampler.green_polynomial_value(partition),
                            oracle.green_polynomial_value(partition),
                        )
                        self.assertEqual(
                            sampler.smaller_distribution(partition),
                            oracle.smaller_distribution(partition),
                        )

    def test_random_stabilizer_element_matches_oracle(self) -> None:
        permutations = [
            (1, 2, 3),
            (2, 1, 3),
            (3, 1, 2, 4),
            (4, 2, 1, 3),
        ]
        for q in (2, 3, 5):
            oracle = SageBurnsideOracle(q)
            sampler = PrimeFieldBurnsideSampler(q)
            for permutation in permutations:
                for seed in range(10):
                    with self.subTest(q=q, permutation=permutation, seed=seed):
                        oracle_rng = random.Random(seed)
                        python_rng = random.Random(seed)
                        oracle_matrix = oracle.random_stabilizer_element(permutation, oracle_rng)
                        python_matrix = sampler.random_stabilizer_element(permutation, python_rng)
                        self.assertEqual(sage_matrix_to_tuple(oracle_matrix), python_matrix)

    def test_jordan_partition_matches_oracle(self) -> None:
        for q in (2, 3, 5):
            oracle = SageBurnsideOracle(q)
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(314159 + q)
            for n in range(1, 6):
                for partition in partitions(n):
                    for _ in range(3):
                        rows = random_general_unipotent_matrix(partition, q, rng)
                        sage_matrix = matrix(oracle.field, [list(row) for row in rows])
                        oracle_jordan, _, oracle_partition = oracle.jordan_data(sage_matrix)
                        python_jordan, _, python_partition = sampler.jordan_form(rows)
                        with self.subTest(q=q, partition=partition, rows=rows):
                            self.assertEqual(python_partition, oracle_partition)
                            self.assertEqual(python_jordan, sage_matrix_to_tuple(oracle_jordan))

    def test_quotient_representation_matches_oracle(self) -> None:
        for q in (2, 3, 5):
            oracle = SageBurnsideOracle(q)
            sampler = PrimeFieldBurnsideSampler(q)
            rng = random.Random(271828 + q)
            for n in range(2, 6):
                permutation = tuple(range(1, n + 1))
                for _ in range(20):
                    python_matrix = sampler.random_stabilizer_element(permutation, rng)
                    sage_matrix = matrix(oracle.field, [list(row) for row in python_matrix])
                    sage_vector = oracle.first_vector_sample(sage_matrix, rng)
                    python_vector = sage_vector_to_tuple(sage_vector)

                    oracle_quotient, oracle_basis = oracle.quotient_representation(sage_matrix, sage_vector)
                    python_quotient, python_basis = sampler.quotient_representation(python_matrix, python_vector)

                    with self.subTest(q=q, n=n, matrix=python_matrix, vector=python_vector):
                        self.assertEqual(python_quotient, sage_matrix_to_tuple(oracle_quotient))
                        self.assertEqual(
                            python_basis,
                            tuple(sage_vector_to_tuple(v) for v in oracle_basis),
                        )


if __name__ == "__main__":
    unittest.main()
