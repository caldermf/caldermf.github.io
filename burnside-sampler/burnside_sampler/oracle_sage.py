"""Sage-backed oracle extracted from `sampling/sampling_burnside.ipynb`.

This module deliberately stays close to the notebook's mathematics while
removing its example cells and global state. It is intended for correctness
tests, not for production deployment.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
from math import comb, factorial
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sage.all import GF, Integer, PolynomialRing, QQ, VectorSpace, identity_matrix, matrix, span, vector

Partition = Tuple[int, ...]


def normalize_partition(parts: Sequence[int]) -> Partition:
    """Normalize a partition into decreasing tuple form."""
    return tuple(sorted((int(part) for part in parts if int(part) > 0), reverse=True))


def sage_vector_to_tuple(v) -> Tuple[int, ...]:
    """Convert a Sage vector over GF(p) into Python integers."""
    return tuple(int(entry) for entry in v)


def sage_matrix_to_tuple(M) -> Tuple[Tuple[int, ...], ...]:
    """Convert a Sage matrix over GF(p) into Python integers."""
    return tuple(tuple(int(entry) for entry in row) for row in M.rows())


class PartitionValue:
    """Notebook-style partition helper."""

    def __init__(self, parts: Sequence[int]):
        self.parts = normalize_partition(parts)

    def __len__(self) -> int:
        return len(self.parts)

    @property
    def total(self) -> int:
        return sum(self.parts)

    def element_at(self, index: int) -> int:
        return self.parts[index]

    def to_row_count_dict(self) -> Dict[int, int]:
        return dict(Counter(self.parts))

    def delete_first_row(self) -> "PartitionValue":
        return PartitionValue(self.parts[1:])

    def concat(self, other: "PartitionValue") -> "PartitionValue":
        return PartitionValue(self.parts + other.parts)

    def to_key(self) -> Partition:
        return self.parts

    def subpartitions(self) -> Iterable["PartitionValue"]:
        counts = self.to_row_count_dict()
        items = list(counts.items())

        def recurse(index: int, chosen: List[Tuple[int, int]]) -> Iterable["PartitionValue"]:
            if index == len(items):
                parts: List[int] = []
                for size, count in chosen:
                    parts.extend([size] * count)
                yield PartitionValue(parts)
                return
            size, multiplicity = items[index]
            for take in range(multiplicity + 1):
                chosen.append((size, take))
                yield from recurse(index + 1, chosen)
                chosen.pop()

        yield from recurse(0, [])


class PolynomialValue:
    """Thin wrapper around Sage polynomials matching the notebook structure."""

    ring = PolynomialRing(QQ, "x")
    x = ring.gen()

    def __init__(self, coeffs=None):
        if coeffs is None:
            self.poly = self.ring(0)
        elif isinstance(coeffs, dict):
            self.poly = sum(QQ(coeff) * self.x ** degree for degree, coeff in coeffs.items())
        else:
            self.poly = sum(QQ(coeff) * self.x ** index for index, coeff in enumerate(coeffs))

    @staticmethod
    def zero() -> "PolynomialValue":
        return PolynomialValue({})

    @staticmethod
    def one() -> "PolynomialValue":
        return PolynomialValue({0: 1})

    def degree(self) -> int:
        return self.poly.degree()

    def __add__(self, other: "PolynomialValue") -> "PolynomialValue":
        result = PolynomialValue()
        result.poly = self.poly + other.poly
        return result

    def __sub__(self, other: "PolynomialValue") -> "PolynomialValue":
        result = PolynomialValue()
        result.poly = self.poly - other.poly
        return result

    def __mul__(self, other: "PolynomialValue") -> "PolynomialValue":
        result = PolynomialValue()
        result.poly = self.poly * other.poly
        return result

    def scalar_multiply(self, scalar) -> "PolynomialValue":
        result = PolynomialValue()
        result.poly = self.poly * QQ(scalar)
        return result

    def involution(self) -> "PolynomialValue":
        degree = self.degree()
        coeffs = {index: self.poly[degree - index] for index in range(degree + 1)}
        return PolynomialValue(coeffs)


def generate_partitions(n: int) -> Iterable[PartitionValue]:
    """Notebook-compatible partition generation."""
    if n == 0:
        yield PartitionValue(())
        return

    def complete_partition_maximally(max_value: int, length: int) -> List[int]:
        if length == 0:
            return []
        quotient, remainder = divmod(length, max_value)
        return [max_value] * quotient + ([remainder] if remainder > 0 else [])

    def next_partition(partition: PartitionValue) -> Optional[PartitionValue]:
        if len(partition) >= 1 and partition.element_at(0) == 1:
            return None
        index = len(partition) - 1
        while index >= 0 and partition.element_at(index) == 1:
            index -= 1
        if index < 0:
            return None
        new_row_value = partition.element_at(index) - 1
        new_parts = list(partition.parts[:index]) + [new_row_value]
        remaining = partition.total - sum(new_parts)
        new_parts.extend(complete_partition_maximally(new_row_value, remaining))
        return PartitionValue(new_parts)

    current = PartitionValue((n,))
    while current is not None:
        yield current
        current = next_partition(current)


class Calculator:
    """Green-polynomial calculator copied from the notebook."""

    def __init__(self):
        self._basic_polys: Dict[int, PolynomialValue] = {}
        self._partition_polys: Dict[Partition, PolynomialValue] = {}
        self._centralizers: Dict[Partition, Integer] = {}
        self._green_polys: Dict[Tuple[Partition, Partition], PolynomialValue] = {}

    def get_basic_polynomial(self, j: int) -> PolynomialValue:
        if j not in self._basic_polys:
            coeffs = [1] + [0] * (j - 1) + [-1]
            self._basic_polys[j] = PolynomialValue(coeffs)
        return self._basic_polys[j]

    def centralizer_size(self, partition: PartitionValue) -> Integer:
        key = partition.to_key()
        if key not in self._centralizers:
            result = Integer(1)
            for size, multiplicity in partition.to_row_count_dict().items():
                result *= size ** multiplicity * factorial(multiplicity)
            self._centralizers[key] = result
        return self._centralizers[key]

    def z_inverse(self, partition: PartitionValue) -> PolynomialValue:
        key = partition.to_key()
        if key not in self._partition_polys:
            result = PolynomialValue.one()
            for part in partition.parts:
                result = result * self.get_basic_polynomial(part)
            self._partition_polys[key] = result.scalar_multiply(1 / self.centralizer_size(partition))
        return self._partition_polys[key]

    def green_polynomial_x(self, lam: PartitionValue, mu: PartitionValue) -> PolynomialValue:
        key = (lam.to_key(), mu.to_key())
        if key in self._green_polys:
            return self._green_polys[key]
        if lam.total != mu.total:
            self._green_polys[key] = PolynomialValue.zero()
            return self._green_polys[key]
        if len(lam) <= 1:
            self._green_polys[key] = PolynomialValue.one()
            return self._green_polys[key]

        result = PolynomialValue.zero()
        mu_count = mu.to_row_count_dict()
        for tau in mu.subpartitions():
            tau_count = tau.to_row_count_dict()
            binomial_product = Integer(1)
            for size in mu_count:
                binomial_product *= comb(mu_count[size], tau_count.get(size, 0))
            remaining_sum = lam.total - lam.element_at(0) - tau.total
            for rho in generate_partitions(remaining_sum):
                term = self.z_inverse(rho) * self.green_polynomial_x(lam.delete_first_row(), tau.concat(rho))
                term = term.scalar_multiply(binomial_product)
                result = result + term if len(rho) % 2 == 0 else result - term

        self._green_polys[key] = result
        return result

    def green_polynomial_q(self, lam: PartitionValue, mu: PartitionValue) -> PolynomialValue:
        return self.green_polynomial_x(lam, mu).involution()


class SageBurnsideOracle:
    """Sage-backed oracle for the Burnside process over prime fields."""

    def __init__(self, q: int):
        q_value = Integer(q)
        if not q_value.is_prime():
            raise ValueError("The oracle is restricted to prime q for this project.")
        self.q = int(q_value)
        self.field = GF(self.q)
        self.calculator = Calculator()

    def green_polynomial(self, lambda_parts: Sequence[int], mu_parts: Sequence[int]):
        """Return the Sage polynomial ``Q_lambda^mu``."""
        lam = PartitionValue(lambda_parts)
        mu = PartitionValue(mu_parts)
        return self.calculator.green_polynomial_q(lam, mu).poly

    @lru_cache(maxsize=None)
    def green_polynomial_value(self, partition: Partition) -> int:
        """Evaluate ``Q_lambda^(1^n)(q)``."""
        lam = PartitionValue(partition)
        mu = PartitionValue((1,) * lam.total)
        polynomial = self.calculator.green_polynomial_q(lam, mu).poly
        return int(polynomial(self.q))

    def smaller_partitions(self, partition: Sequence[int]) -> List[Partition]:
        """Notebook-compatible one-box removals."""
        normalized = list(normalize_partition(partition))
        result = set()
        for index, part in enumerate(normalized):
            updated = normalized.copy()
            updated[index] = part - 1
            if updated[index] == 0:
                updated.pop(index)
            result.add(tuple(sorted(updated, reverse=True)))
        return sorted(result, reverse=True)

    def which_removed(self, partition: Sequence[int], smaller: Sequence[int]) -> int:
        """Notebook-compatible index of the decremented part."""
        large = list(normalize_partition(partition))
        small = list(normalize_partition(smaller))
        for index, part in enumerate(large):
            if index >= len(small) or part - small[index] == 1:
                return index
        raise ValueError("No single decrement/removal found.")

    def multiplicity(self, partition: Sequence[int], index: int) -> int:
        """Multiplicity of the part at ``index``."""
        normalized = list(normalize_partition(partition))
        return normalized.count(normalized[index])

    def flag_amount(self, partition: Sequence[int], smaller: Sequence[int]) -> int:
        """Size of ``E^{lambda'}(lambda)`` from the notebook."""
        decremented_index = self.which_removed(partition, smaller)
        mult = self.multiplicity(partition, decremented_index)
        return (self.q ** mult - 1) * (self.q ** (decremented_index + 1 - mult))

    def smaller_weights(self, partition: Sequence[int]) -> Dict[Partition, int]:
        """Integer one-box-removal weights."""
        normalized = normalize_partition(partition)
        return {
            smaller: self.flag_amount(normalized, smaller) * self.green_polynomial_value(smaller)
            for smaller in self.smaller_partitions(normalized)
        }

    def smaller_distribution(self, partition: Sequence[int]) -> Dict[Partition, Fraction]:
        """Exact normalized one-box-removal distribution."""
        weights = self.smaller_weights(partition)
        total = sum(weights.values())
        return {smaller: Fraction(weight, total) for smaller, weight in weights.items()}

    def _weighted_choice(self, items: Sequence[Partition], weights: Sequence[int], rng: Optional[random.Random]) -> Partition:
        generator = rng or random
        total = sum(weights)
        ticket = generator.randrange(total)
        seen = 0
        for item, weight in zip(items, weights):
            seen += weight
            if ticket < seen:
                return item
        return items[-1]

    def _random_field_element(self, rng: Optional[random.Random]):
        generator = rng or random
        return self.field(generator.randrange(self.q))

    def random_nonzero_vector(self, length: int, rng: Optional[random.Random] = None):
        """Notebook-compatible nonzero vector sampler."""
        generator = rng or random
        index = generator.randrange(1, self.q ** length)
        coords = []
        for _ in range(length):
            coords.append(self.field(index % self.q))
            index //= self.q
        return vector(self.field, coords)

    def random_vector(self, length: int, rng: Optional[random.Random] = None):
        """Uniform random vector in ``F_q^length``."""
        return vector(self.field, [self._random_field_element(rng) for _ in range(length)])

    def random_stabilizer_element(self, permutation: Sequence[int], rng: Optional[random.Random] = None):
        """Uniform random element of ``U_w``."""
        entries = list(int(value) for value in permutation)
        n = len(entries)
        if min(entries) == 0:
            entries = [value + 1 for value in entries]
        inverse = [0] * n
        for index, image in enumerate(entries):
            inverse[image - 1] = index + 1

        M = identity_matrix(self.field, n)
        for row in range(n):
            for col in range(row + 1, n):
                if inverse[row] <= inverse[col]:
                    M[row, col] = self._random_field_element(rng)
        return M

    def all_stabilizer_elements(self, permutation: Sequence[int]) -> List:
        """Enumerate the stabilizer ``U_w`` for small exact tests."""
        entries = list(int(value) for value in permutation)
        n = len(entries)
        if min(entries) == 0:
            entries = [value + 1 for value in entries]
        inverse = [0] * n
        for index, image in enumerate(entries):
            inverse[image - 1] = index + 1

        free_positions: List[Tuple[int, int]] = []
        for row in range(n):
            for col in range(row + 1, n):
                if inverse[row] <= inverse[col]:
                    free_positions.append((row, col))

        total = self.q ** len(free_positions)
        matrices = []
        for ticket in range(total):
            M = identity_matrix(self.field, n)
            value = ticket
            for row, col in free_positions:
                M[row, col] = self.field(value % self.q)
                value //= self.q
            matrices.append(M)
        return matrices

    def quotient_representation(self, M, v):
        """Induced quotient action on ``V / <v>``."""
        ambient = VectorSpace(self.field, M.nrows())
        vec = ambient(v)
        if M * vec != vec:
            raise ValueError("Input vector v must be an eigenvector with eigenvalue 1.")

        basis = [vec]
        for candidate in ambient.basis():
            if len(basis) == M.nrows():
                break
            if candidate not in span(basis):
                basis.append(candidate)

        P = matrix(self.field, basis).transpose()
        Pinv = P.inverse()
        conjugated = Pinv * M * P
        return conjugated[1:, 1:], tuple(basis)

    def lift(self, quotient_vector, basis):
        """Lift quotient coordinates using the notebook convention."""
        coefficients = vector(self.field, quotient_vector)
        result = vector(self.field, [self.field(0)] * len(basis[0]))
        for coeff, basis_vector in zip(coefficients, basis[1:]):
            result += coeff * basis_vector
        return result

    def jordan_data(self, A):
        """Return ``(J, P, partition)`` from Sage's Jordan form."""
        J, P = A.jordan_form(transformation=True)
        partition: List[int] = []
        index = 0
        while index < J.nrows():
            size = 1
            while index + size < J.nrows() and J[index + size - 1, index + size] == 1:
                size += 1
            partition.append(size)
            index += size
        return J, P, tuple(partition)

    def first_vector_sample(self, A, rng: Optional[random.Random] = None):
        """Sample the first flag vector exactly as in the notebook."""
        _, P, partition = self.jordan_data(A)
        weights = self.smaller_weights(partition)
        choices = list(weights)
        smaller = self._weighted_choice(choices, [weights[choice] for choice in choices], rng)

        padded = list(smaller) + [0] * (len(partition) - len(smaller))
        decremented_size = None
        for part, smaller_part in zip(partition, padded):
            if part != smaller_part:
                decremented_size = part
                break
        if decremented_size is None:
            raise ValueError("Could not determine the decremented Jordan block size.")

        starts = []
        offset = 0
        for part in partition:
            starts.append(offset)
            offset += part

        equal_indices = [start for start, part in zip(starts, partition) if part == decremented_size]
        greater_indices = [start for start, part in zip(starts, partition) if part > decremented_size]

        coords = vector(self.field, [self.field(0)] * sum(partition))
        if equal_indices:
            equal_vector = self.random_nonzero_vector(len(equal_indices), rng)
            for index, value in zip(equal_indices, equal_vector):
                coords[index] = value
        if greater_indices:
            greater_vector = self.random_vector(len(greater_indices), rng)
            for index, value in zip(greater_indices, greater_vector):
                coords[index] = value
        return P * coords

    def springer_sample_flag(self, A, rng: Optional[random.Random] = None):
        """Sample a complete Springer-fiber flag."""
        n = A.nrows()
        if n == 1:
            return [vector(self.field, [self.field(1)])]

        first = self.first_vector_sample(A, rng)
        flag = [first]
        quotient, basis = self.quotient_representation(A, first)
        for quotient_vector in self.springer_sample_flag(quotient, rng):
            flag.append(self.lift(quotient_vector, basis))
        return flag

    def flag_to_permutation(self, flag: Sequence[Sequence[int]]) -> Tuple[int, ...]:
        """Convert a flag to a permutation using rightmost pivots."""
        rows = [list(vector(self.field, row)) for row in flag]
        if not rows:
            return tuple()

        n = len(rows[0])
        pivots: List[int] = []
        for index in range(len(rows)):
            for previous_row, pivot_col in enumerate(pivots):
                if rows[index][pivot_col] == 0:
                    continue
                factor = rows[index][pivot_col] / rows[previous_row][pivot_col]
                for col in range(n):
                    rows[index][col] -= factor * rows[previous_row][col]

            pivot = next((col for col in range(n - 1, -1, -1) if rows[index][col] != 0), None)
            if pivot is None:
                raise ValueError("Input rows are not a strict flag.")
            pivots.append(pivot)
        return tuple(pivot + 1 for pivot in pivots)

    def next_step(self, permutation: Sequence[int], rng: Optional[random.Random] = None) -> Tuple[int, ...]:
        """One Burnside-process step."""
        stabilizer = self.random_stabilizer_element(permutation, rng)
        flag = self.springer_sample_flag(stabilizer, rng)
        return self.flag_to_permutation(flag)
