"""Pure-Python Burnside sampler for prime fields.

This module is a careful port of the trusted Sage notebook
`sampling/sampling_burnside.ipynb`. The implementation keeps the same
mathematical structure while replacing Sage matrices, vector spaces, and
Jordan-form support with small finite-field linear algebra routines over
prime fields F_p.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

Partition = Tuple[int, ...]
Vector = Tuple[int, ...]
Matrix = Tuple[Tuple[int, ...], ...]


def rsk_insertion_tableau(permutation: Sequence[int]) -> Tuple[Tuple[int, ...], ...]:
    """Return the RSK insertion tableau ``P`` of a permutation."""
    tableau: List[List[int]] = []
    for raw_value in permutation:
        carried = int(raw_value)
        inserted = False
        for row in tableau:
            bump_index = next((index for index, value in enumerate(row) if value > carried), None)
            if bump_index is None:
                row.append(carried)
                inserted = True
                break
            row[bump_index], carried = carried, row[bump_index]
        if not inserted:
            tableau.append([carried])
    return tuple(tuple(row) for row in tableau)


def tableau_key(tableau: Sequence[Sequence[int]]) -> str:
    """Serialize a tableau into a stable key suitable for UI metadata."""
    return "|".join(",".join(str(int(value)) for value in row) for row in tableau)


def right_steinberg_cell_key(permutation: Sequence[int]) -> str:
    """Return the right-cell key determined by the RSK insertion tableau ``P``."""
    return tableau_key(rsk_insertion_tableau(permutation))


def is_prime(n: int) -> bool:
    """Return whether ``n`` is prime."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    trial = 3
    while trial * trial <= n:
        if n % trial == 0:
            return False
        trial += 2
    return True


def normalize_partition(parts: Sequence[int]) -> Partition:
    """Normalize a partition into decreasing tuple form."""
    return tuple(sorted((int(part) for part in parts if int(part) > 0), reverse=True))


def normalize_vector(vector: Sequence[int], q: int) -> Vector:
    """Reduce a vector modulo ``q``."""
    return tuple(int(entry) % q for entry in vector)


def normalize_matrix(rows: Sequence[Sequence[int]], q: int) -> Matrix:
    """Reduce a matrix modulo ``q``."""
    return tuple(normalize_vector(row, q) for row in rows)


def zero_vector(n: int) -> Vector:
    """Return the zero vector in ``F_q^n``."""
    return tuple(0 for _ in range(n))


def identity_matrix(n: int) -> Matrix:
    """Return the identity matrix of size ``n``."""
    return tuple(
        tuple(1 if row == col else 0 for col in range(n))
        for row in range(n)
    )


def matrix_from_columns(columns: Sequence[Sequence[int]], q: int) -> Matrix:
    """Build a matrix whose columns are the supplied vectors."""
    if not columns:
        return tuple()
    height = len(columns[0])
    width = len(columns)
    return tuple(
        tuple(int(columns[col][row]) % q for col in range(width))
        for row in range(height)
    )


def mod_inv(a: int, q: int) -> int:
    """Multiplicative inverse in ``F_q`` for prime ``q``."""
    value = int(a) % q
    if value == 0:
        raise ZeroDivisionError("Cannot invert zero modulo q.")
    return pow(value, q - 2, q)


def mat_sub(A: Matrix, B: Matrix, q: int) -> Matrix:
    """Matrix subtraction modulo ``q``."""
    return tuple(
        tuple((int(a) - int(b)) % q for a, b in zip(row_a, row_b))
        for row_a, row_b in zip(A, B)
    )


def mat_mul(A: Matrix, B: Matrix, q: int) -> Matrix:
    """Matrix multiplication modulo ``q``."""
    n_rows = len(A)
    n_cols = len(B[0]) if B else 0
    inner = len(B)
    product: List[Tuple[int, ...]] = []
    for row in range(n_rows):
        entries = []
        for col in range(n_cols):
            total = 0
            for index in range(inner):
                total += int(A[row][index]) * int(B[index][col])
            entries.append(total % q)
        product.append(tuple(entries))
    return tuple(product)


def mat_vec(M: Matrix, v: Vector, q: int) -> Vector:
    """Matrix-vector multiplication modulo ``q``."""
    return tuple(
        sum(int(entry) * int(coeff) for entry, coeff in zip(row, v)) % q
        for row in M
    )


def submatrix(A: Matrix, row_start: int, col_start: int) -> Matrix:
    """Return the lower-right block of ``A``."""
    return tuple(
        tuple(row[col_start:])
        for row in A[row_start:]
    )


def row_reduce(rows: Sequence[Sequence[int]], q: int) -> Tuple[List[List[int]], List[int]]:
    """Reduced row echelon form and pivot columns."""
    matrix = [list(normalize_vector(row, q)) for row in rows]
    if not matrix:
        return [], []
    n_rows = len(matrix)
    n_cols = len(matrix[0])
    pivot_cols: List[int] = []
    pivot_row = 0
    for col in range(n_cols):
        chosen = next((row for row in range(pivot_row, n_rows) if matrix[row][col] % q), None)
        if chosen is None:
            continue
        matrix[pivot_row], matrix[chosen] = matrix[chosen], matrix[pivot_row]
        inv = mod_inv(matrix[pivot_row][col], q)
        matrix[pivot_row] = [(entry * inv) % q for entry in matrix[pivot_row]]
        for row in range(n_rows):
            if row == pivot_row or matrix[row][col] % q == 0:
                continue
            factor = matrix[row][col] % q
            matrix[row] = [
                (entry - factor * pivot) % q
                for entry, pivot in zip(matrix[row], matrix[pivot_row])
            ]
        pivot_cols.append(col)
        pivot_row += 1
        if pivot_row == n_rows:
            break
    return matrix, pivot_cols


def rank(rows: Sequence[Sequence[int]], q: int) -> int:
    """Rank of the row-span generated by ``rows``."""
    _, pivot_cols = row_reduce(rows, q)
    return len(pivot_cols)


def in_span(vector: Sequence[int], basis: Sequence[Sequence[int]], q: int) -> bool:
    """Check whether ``vector`` lies in the span of ``basis``."""
    vec = normalize_vector(vector, q)
    if not basis:
        return vec == zero_vector(len(vec))
    return rank(basis, q) == rank(list(basis) + [vec], q)


def independent_basis(vectors: Iterable[Sequence[int]], q: int) -> List[Vector]:
    """Extract a basis in first-appearance order."""
    basis: List[Vector] = []
    for vector in vectors:
        normalized = normalize_vector(vector, q)
        if not in_span(normalized, basis, q):
            basis.append(normalized)
    return basis


def kernel_basis(M: Matrix, q: int) -> List[Vector]:
    """Basis for the kernel of ``M`` over ``F_q``."""
    reduced, pivot_cols = row_reduce(M, q)
    n_cols = len(M[0]) if M else 0
    free_cols = [col for col in range(n_cols) if col not in pivot_cols]
    basis: List[Vector] = []
    for free in free_cols:
        vector = [0] * n_cols
        vector[free] = 1
        for row, pivot in enumerate(pivot_cols):
            vector[pivot] = (-reduced[row][free]) % q
        basis.append(tuple(vector))
    return basis


def complement_basis(space_basis: Sequence[Sequence[int]], subspace_basis: Sequence[Sequence[int]], q: int) -> List[Vector]:
    """Choose vectors in ``space_basis`` extending ``subspace_basis``."""
    current = independent_basis(subspace_basis, q)
    complement: List[Vector] = []
    for vector in independent_basis(space_basis, q):
        if not in_span(vector, current, q):
            current.append(vector)
            complement.append(vector)
    return complement


def mat_inv(M: Matrix, q: int) -> Matrix:
    """Matrix inverse over ``F_q``."""
    n = len(M)
    augmented = [
        list(row) + [1 if row_index == col else 0 for col in range(n)]
        for row_index, row in enumerate(normalize_matrix(M, q))
    ]
    for col in range(n):
        pivot = next((row for row in range(col, n) if augmented[row][col] % q), None)
        if pivot is None:
            raise ZeroDivisionError("Matrix does not have full rank.")
        augmented[col], augmented[pivot] = augmented[pivot], augmented[col]
        inv = mod_inv(augmented[col][col], q)
        augmented[col] = [(entry * inv) % q for entry in augmented[col]]
        for row in range(n):
            if row == col or augmented[row][col] % q == 0:
                continue
            factor = augmented[row][col] % q
            augmented[row] = [
                (entry - factor * pivot_entry) % q
                for entry, pivot_entry in zip(augmented[row], augmented[col])
            ]
    return tuple(tuple(row[n:]) for row in augmented)


@lru_cache(maxsize=None)
def partitions(n: int) -> Tuple[Partition, ...]:
    """All partitions of ``n`` in decreasing order."""
    if n == 0:
        return ((),)
    result: List[Partition] = []

    def generate(remaining: int, max_part: int, current: List[int]) -> None:
        if remaining == 0:
            result.append(tuple(current))
            return
        for part in range(min(remaining, max_part), 0, -1):
            current.append(part)
            generate(remaining - part, part, current)
            current.pop()

    generate(n, n, [])
    return tuple(result)


def smaller_partitions(partition: Sequence[int]) -> List[Partition]:
    """All partitions obtained by deleting one box from ``partition``."""
    normalized = list(normalize_partition(partition))
    result = set()
    for index, part in enumerate(normalized):
        updated = normalized.copy()
        updated[index] = part - 1
        if updated[index] == 0:
            updated.pop(index)
        result.add(tuple(sorted(updated, reverse=True)))
    return sorted(result, reverse=True)


def which_removed(partition: Sequence[int], smaller: Sequence[int]) -> int:
    """Index of the decremented part using the notebook convention."""
    large = list(normalize_partition(partition))
    small = list(normalize_partition(smaller))
    for index, part in enumerate(large):
        if index >= len(small) or part - small[index] == 1:
            return index
    raise ValueError("No single decrement/removal found.")


def multiplicity(partition: Sequence[int], index: int) -> int:
    """Multiplicity of the part at ``index``."""
    normalized = list(normalize_partition(partition))
    return normalized.count(normalized[index])


def flag_amount(partition: Sequence[int], smaller: Sequence[int], q: int) -> int:
    """Size of ``E^{lambda'}(lambda)`` in the notebook convention."""
    decremented_index = which_removed(partition, smaller)
    mult = multiplicity(partition, decremented_index)
    return (q ** mult - 1) * (q ** (decremented_index + 1 - mult))


def block_starts(partition: Sequence[int]) -> List[int]:
    """Starting indices of Jordan blocks."""
    starts: List[int] = []
    offset = 0
    for part in normalize_partition(partition):
        starts.append(offset)
        offset += part
    return starts


def z_lambda(partition: Sequence[int]) -> int:
    """Centralizer size ``z_lambda``."""
    result = 1
    counts = Counter(normalize_partition(partition))
    for part, mult in counts.items():
        factorial = 1
        for value in range(2, mult + 1):
            factorial *= value
        result *= (part ** mult) * factorial
    return result


def polynomial_multiply(left: Sequence[Fraction], right: Sequence[Fraction]) -> Tuple[Fraction, ...]:
    """Multiply two polynomials represented by coefficient tuples."""
    if not left or not right:
        return (Fraction(0),)
    result = [Fraction(0)] * (len(left) + len(right) - 1)
    for left_index, left_coeff in enumerate(left):
        for right_index, right_coeff in enumerate(right):
            result[left_index + right_index] += left_coeff * right_coeff
    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


@lru_cache(maxsize=None)
def green_polynomial_x(lam: Partition, mu: Partition) -> Tuple[Fraction, ...]:
    """Green polynomial ``X_lambda^mu`` as a coefficient tuple."""
    lam = normalize_partition(lam)
    mu = normalize_partition(mu)
    if sum(lam) != sum(mu):
        return (Fraction(0),)
    if len(lam) <= 1:
        return (Fraction(1),)

    mu_counts = Counter(mu)
    leading = lam[0]
    remainder = lam[1:]
    result = [Fraction(0)]

    def subpartitions(items: List[Tuple[int, int]], index: int = 0, chosen: Tuple[Tuple[int, int], ...] = ()) -> Iterable[Partition]:
        if index == len(items):
            parts: List[int] = []
            for size, take in chosen:
                parts.extend([size] * take)
            yield tuple(sorted(parts, reverse=True))
            return
        size, count = items[index]
        for take in range(count + 1):
            yield from subpartitions(items, index + 1, chosen + ((size, take),))

    for tau in subpartitions(list(mu_counts.items())):
        tau_counts = Counter(tau)
        binomial_product = Fraction(1)
        for size, count in mu_counts.items():
            take = tau_counts.get(size, 0)
            numerator = 1
            denominator = 1
            for offset in range(take):
                numerator *= (count - offset)
                denominator *= (offset + 1)
            binomial_product *= Fraction(numerator, denominator)
        remaining = sum(lam) - leading - sum(tau)
        for rho in partitions(remaining):
            concat = tuple(sorted(tau + rho, reverse=True))
            z_inverse = [Fraction(1)]
            for part in rho:
                next_poly = [Fraction(0)] * (len(z_inverse) + part)
                for index, coeff in enumerate(z_inverse):
                    next_poly[index] += coeff
                    next_poly[index + part] -= coeff
                z_inverse = next_poly
            centralizer = z_lambda(rho)
            z_inverse = [coeff / centralizer for coeff in z_inverse]
            recursive = green_polynomial_x(remainder, concat)
            term = polynomial_multiply(tuple(z_inverse), recursive)
            sign = 1 if len(rho) % 2 == 0 else -1
            while len(result) < len(term):
                result.append(Fraction(0))
            for index, coeff in enumerate(term):
                result[index] += sign * binomial_product * coeff

    while len(result) > 1 and result[-1] == 0:
        result.pop()
    return tuple(result)


def green_polynomial_q(lam: Sequence[int], mu: Sequence[int]) -> Tuple[Fraction, ...]:
    """Green polynomial ``Q_lambda^mu``."""
    return tuple(reversed(green_polynomial_x(normalize_partition(lam), normalize_partition(mu))))


@lru_cache(maxsize=None)
def green_polynomial_value(partition: Partition, q: int) -> int:
    """Evaluate ``Q_lambda^(1^n)(q)``."""
    normalized = normalize_partition(partition)
    n = sum(normalized)
    polynomial = green_polynomial_q(normalized, (1,) * n)
    value = Fraction(0)
    for degree, coeff in enumerate(polynomial):
        value += coeff * (q ** degree)
    return int(value)


def weighted_choice(items: Sequence[Partition], weights: Sequence[int], rng: Optional[random.Random] = None) -> Partition:
    """Choose from ``items`` with integer weights."""
    if len(items) != len(weights):
        raise ValueError("Items and weights must have the same length.")
    total = sum(weights)
    if total <= 0:
        raise ValueError("At least one positive weight is required.")
    generator = rng or random
    ticket = generator.randrange(total)
    seen = 0
    for item, weight in zip(items, weights):
        seen += weight
        if ticket < seen:
            return item
    return items[-1]


def random_nonzero_vector(length: int, q: int, rng: Optional[random.Random] = None) -> Vector:
    """Uniform random nonzero vector in ``F_q^length`` using notebook digit order."""
    if length <= 0:
        return tuple()
    generator = rng or random
    index = generator.randrange(1, q ** length)
    coords: List[int] = []
    for _ in range(length):
        coords.append(index % q)
        index //= q
    return tuple(coords)


def random_vector(length: int, q: int, rng: Optional[random.Random] = None) -> Vector:
    """Uniform random vector in ``F_q^length``."""
    generator = rng or random
    return tuple(generator.randrange(q) for _ in range(length))


def jordan_form_unipotent(A: Sequence[Sequence[int]], q: int) -> Tuple[Matrix, Matrix, Partition]:
    """Jordan form of a unipotent matrix over ``F_q``."""
    matrix = normalize_matrix(A, q)
    n = len(matrix)
    identity = identity_matrix(n)
    nilpotent = mat_sub(matrix, identity, q)

    powers = [identity]
    kernels: List[List[Vector]] = [[]]
    dims = [0]
    current = identity
    for _ in range(1, n + 1):
        current = mat_mul(current, nilpotent, q)
        powers.append(current)
        basis = kernel_basis(current, q)
        kernels.append(basis)
        dims.append(len(basis))
        if dims[-1] == n:
            break

    max_size = len(dims) - 1
    blocks_at_least = [0] * (max_size + 2)
    for size in range(1, max_size + 1):
        blocks_at_least[size] = dims[size] - dims[size - 1]

    partition_parts: List[int] = []
    chain_generators_by_size: Dict[int, List[Vector]] = {}
    for size in range(max_size, 0, -1):
        exact_blocks = blocks_at_least[size] - blocks_at_least[size + 1]
        if exact_blocks <= 0:
            continue
        previous_kernel = kernels[size - 1]
        next_image = []
        if size < max_size:
            next_image = [mat_vec(nilpotent, vector, q) for vector in kernels[size + 1]]
        spanning_basis = independent_basis(previous_kernel + next_image, q)
        generators = complement_basis(kernels[size], spanning_basis, q)
        if len(generators) != exact_blocks:
            raise ValueError(
                f"Could not construct Jordan generators for block size {size}: "
                f"expected {exact_blocks}, found {len(generators)}."
            )
        chain_generators_by_size[size] = generators
        partition_parts.extend([size] * exact_blocks)

    partition = tuple(partition_parts)
    columns: List[Vector] = []
    for size in partition:
        generator = chain_generators_by_size[size].pop(0)
        chain = [generator]
        for _ in range(size - 1):
            chain.append(mat_vec(nilpotent, chain[-1], q))
        columns.extend(reversed(chain))

    if len(columns) != n:
        raise ValueError("Jordan basis construction did not produce n columns.")

    P = matrix_from_columns(columns, q)
    Pinv = mat_inv(P, q)

    J_rows = [list(row) for row in identity]
    offset = 0
    for size in partition:
        for index in range(size - 1):
            J_rows[offset + index][offset + index + 1] = 1
        offset += size
    J = normalize_matrix(J_rows, q)

    reconstructed = mat_mul(mat_mul(P, J, q), Pinv, q)
    if reconstructed != matrix:
        raise ValueError("Jordan decomposition failed to reconstruct the input matrix.")

    return J, P, partition


class PrimeFieldBurnsideSampler:
    """Burnside sampler over a prime field ``F_q``."""

    def __init__(self, q: int):
        if not is_prime(q):
            raise ValueError("This implementation only supports prime q.")
        self.q = int(q)

    def green_polynomial_value(self, partition: Sequence[int]) -> int:
        """Return ``Q_lambda^(1^n)(q)``."""
        return green_polynomial_value(normalize_partition(partition), self.q)

    def smaller_weights(self, partition: Sequence[int]) -> Dict[Partition, int]:
        """Integer sampling weights for one-box removals of ``partition``."""
        normalized = normalize_partition(partition)
        return {
            smaller: flag_amount(normalized, smaller, self.q) * self.green_polynomial_value(smaller)
            for smaller in smaller_partitions(normalized)
        }

    def smaller_distribution(self, partition: Sequence[int]) -> Dict[Partition, Fraction]:
        """Exact normalized distribution on one-box removals of ``partition``."""
        weights = self.smaller_weights(partition)
        total = sum(weights.values())
        return {
            smaller: Fraction(weight, total)
            for smaller, weight in weights.items()
        }

    def random_stabilizer_element(self, permutation: Sequence[int], rng: Optional[random.Random] = None) -> Matrix:
        """Uniform random element of the stabilizer ``U_w``."""
        generator = rng or random
        entries = list(int(value) for value in permutation)
        n = len(entries)
        if min(entries) == 0:
            entries = [value + 1 for value in entries]
        inverse = [0] * n
        for index, image in enumerate(entries):
            inverse[image - 1] = index + 1

        rows = [list(row) for row in identity_matrix(n)]
        for row in range(n):
            for col in range(row + 1, n):
                if inverse[row] <= inverse[col]:
                    rows[row][col] = generator.randrange(self.q)
        return normalize_matrix(rows, self.q)

    def all_stabilizer_elements(self, permutation: Sequence[int]) -> List[Matrix]:
        """Enumerate the stabilizer ``U_w``. Intended for small test cases."""
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
        matrices: List[Matrix] = []
        for ticket in range(total):
            rows = [list(row) for row in identity_matrix(n)]
            value = ticket
            for row, col in free_positions:
                rows[row][col] = value % self.q
                value //= self.q
            matrices.append(normalize_matrix(rows, self.q))
        return matrices

    def jordan_form(self, A: Sequence[Sequence[int]]) -> Tuple[Matrix, Matrix, Partition]:
        """Jordan form of a unipotent matrix over ``F_q``."""
        return jordan_form_unipotent(A, self.q)

    def quotient_representation(self, A: Sequence[Sequence[int]], v: Sequence[int]) -> Tuple[Matrix, Tuple[Vector, ...]]:
        """Induced action of ``A`` on ``V / <v>``."""
        matrix = normalize_matrix(A, self.q)
        vector = normalize_vector(v, self.q)
        if mat_vec(matrix, vector, self.q) != vector:
            raise ValueError("Input vector v must be an eigenvector with eigenvalue 1.")

        n = len(matrix)
        basis: List[Vector] = [vector]
        for index in range(n):
            candidate = tuple(1 if i == index else 0 for i in range(n))
            if not in_span(candidate, basis, self.q):
                basis.append(candidate)
            if len(basis) == n:
                break
        if len(basis) != n:
            raise ValueError("Could not extend v to a basis.")

        P = matrix_from_columns(basis, self.q)
        Pinv = mat_inv(P, self.q)
        conjugated = mat_mul(mat_mul(Pinv, matrix, self.q), P, self.q)
        return submatrix(conjugated, 1, 1), tuple(basis)

    def lift(self, quotient_vector: Sequence[int], basis: Sequence[Sequence[int]]) -> Vector:
        """Lift quotient coordinates back into the ambient space."""
        result = [0] * len(basis[0])
        for coeff, vector in zip(normalize_vector(quotient_vector, self.q), basis[1:]):
            for index, entry in enumerate(vector):
                result[index] = (result[index] + coeff * int(entry)) % self.q
        return tuple(result)

    def _sample_first_vector_from_jordan_data(
        self,
        partition: Partition,
        change_of_basis: Matrix,
        rng: Optional[random.Random] = None,
    ) -> Tuple[Vector, Partition, Dict[Partition, int]]:
        """Sample the first vector given Jordan data."""
        generator = rng or random
        weights = self.smaller_weights(partition)
        choices = list(weights)
        smaller = weighted_choice(choices, [weights[choice] for choice in choices], generator)

        padded = list(smaller) + [0] * (len(partition) - len(smaller))
        decremented_size = None
        for part, smaller_part in zip(partition, padded):
            if part != smaller_part:
                decremented_size = part
                break
        if decremented_size is None:
            raise ValueError("Could not determine the decremented Jordan block size.")

        n = sum(partition)
        starts = block_starts(partition)
        equal_indices = [start for start, part in zip(starts, partition) if part == decremented_size]
        greater_indices = [start for start, part in zip(starts, partition) if part > decremented_size]

        jordan_coords = [0] * n
        if equal_indices:
            equal_vector = random_nonzero_vector(len(equal_indices), self.q, generator)
            for index, entry in zip(equal_indices, equal_vector):
                jordan_coords[index] = entry
        if greater_indices:
            larger_vector = random_vector(len(greater_indices), self.q, generator)
            for index, entry in zip(greater_indices, larger_vector):
                jordan_coords[index] = entry

        return mat_vec(change_of_basis, tuple(jordan_coords), self.q), smaller, weights

    def first_vector_sample(self, A: Sequence[Sequence[int]], rng: Optional[random.Random] = None) -> Vector:
        """Sample the first vector in a Springer fiber flag."""
        _, change_of_basis, partition = self.jordan_form(A)
        vector, _, _ = self._sample_first_vector_from_jordan_data(partition, change_of_basis, rng)
        return vector

    def _springer_sample_flag_with_trace(
        self,
        A: Sequence[Sequence[int]],
        rng: Optional[random.Random] = None,
    ) -> Tuple[List[Vector], List[Dict[str, object]]]:
        """Sample a flag and record the recursive quotient trace."""
        matrix = normalize_matrix(A, self.q)
        n = len(matrix)
        if n == 1:
            return [(1,)], [
                {
                    "dimension": 1,
                    "matrix": matrix,
                    "partition": (1,),
                    "smaller_partition": (),
                    "smaller_weights": {},
                    "first_vector": (1,),
                    "quotient": tuple(),
                }
            ]

        _, change_of_basis, partition = self.jordan_form(matrix)
        vector, smaller, weights = self._sample_first_vector_from_jordan_data(partition, change_of_basis, rng)
        quotient, basis = self.quotient_representation(matrix, vector)
        sub_flag, sub_trace = self._springer_sample_flag_with_trace(quotient, rng)
        flag = [vector]
        for quotient_vector in sub_flag:
            flag.append(self.lift(quotient_vector, basis))
        trace = [
            {
                "dimension": n,
                "matrix": matrix,
                "partition": partition,
                "smaller_partition": smaller,
                "smaller_weights": dict(weights),
                "first_vector": vector,
                "quotient": quotient,
            }
        ]
        trace.extend(sub_trace)
        return flag, trace

    def springer_sample_flag(self, A: Sequence[Sequence[int]], rng: Optional[random.Random] = None) -> List[Vector]:
        """Sample a complete flag from the Springer fiber of ``A``."""
        flag, _ = self._springer_sample_flag_with_trace(A, rng)
        return flag

    def flag_to_permutation(self, flag: Sequence[Sequence[int]]) -> Tuple[int, ...]:
        """Convert a flag to its right-pivot permutation."""
        rows = [list(normalize_vector(vector, self.q)) for vector in flag]
        if not rows:
            return tuple()

        n = len(rows[0])
        pivots: List[int] = []
        for row_index in range(len(rows)):
            for previous_row, pivot_col in enumerate(pivots):
                if rows[row_index][pivot_col] == 0:
                    continue
                factor = (rows[row_index][pivot_col] * mod_inv(rows[previous_row][pivot_col], self.q)) % self.q
                rows[row_index] = [
                    (entry - factor * pivot) % self.q
                    for entry, pivot in zip(rows[row_index], rows[previous_row])
                ]

            pivot = next((col for col in range(n - 1, -1, -1) if rows[row_index][col] != 0), None)
            if pivot is None:
                raise ValueError("Input rows are not a strict flag.")
            pivots.append(pivot)

        return tuple(pivot + 1 for pivot in pivots)

    def next_step(self, permutation: Sequence[int], rng: Optional[random.Random] = None) -> Tuple[int, ...]:
        """One Burnside-process step."""
        stabilizer = self.random_stabilizer_element(permutation, rng)
        flag = self.springer_sample_flag(stabilizer, rng)
        return self.flag_to_permutation(flag)

    def next_step_with_details(
        self,
        permutation: Sequence[int],
        rng: Optional[random.Random] = None,
    ) -> Dict[str, object]:
        """One Burnside-process step with a serialized trace for UI use."""
        current = tuple(int(value) for value in permutation)
        stabilizer = self.random_stabilizer_element(current, rng)
        flag, trace = self._springer_sample_flag_with_trace(stabilizer, rng)
        next_permutation = self.flag_to_permutation(flag)
        return {
            "current": current,
            "stabilizer": stabilizer,
            "flag": flag,
            "trace": trace,
            "next": next_permutation,
        }

    def run_chain(
        self,
        n: int,
        steps: int,
        start: Optional[Sequence[int]] = None,
        rng: Optional[random.Random] = None,
    ) -> List[Tuple[int, ...]]:
        """Run the Burnside chain for ``steps`` iterations."""
        current = tuple(start) if start is not None else tuple(range(1, n + 1))
        history = [current]
        for _ in range(steps):
            current = self.next_step(current, rng)
            history.append(current)
        return history
