# Greens Polynomial Stuff

from fractions import Fraction
from functools import lru_cache
from math import comb
from collections import Counter
from typing import Tuple, Dict, Iterator, List

# -------------------------
# Factorial and Binomial Coefficient Calculators (matching JS structure)
# -------------------------
class FactorialCalculator:
    def __init__(self):
        self.cache = {0: 1, 1: 1}
    
    def get(self, n: int) -> int:
        if n == 0 or n == 1:
            return 1
        
        current_number = n
        while current_number not in self.cache:
            current_number -= 1
        
        value = self.cache[current_number]
        for i in range(current_number + 1, n + 1):
            value = value * i
            self.cache[i] = value
        
        return value

class BinomialCoefficientCalculator:
    def __init__(self):
        self.cache = {}
    
    def get(self, n: int, k: int) -> int:
        if k < 0 or k > n:
            return 0
        if k == 0 or k == n:
            return 1
        
        k = min(k, n - k)
        key = f"{n},{k}"
        
        if key in self.cache:
            return self.cache[key]
        
        result = self.get(n - 1, k - 1) + self.get(n - 1, k)
        self.cache[key] = result
        return result

# -------------------------
# Partition helper
# -------------------------
class Partition:
    def __init__(self, parts):
        # normalize to nonincreasing tuple of positive ints
        parts = tuple(int(p) for p in parts if p > 0)
        parts = tuple(sorted(parts, reverse=True))
        self.parts = parts

    def __len__(self):
        return len(self.parts)

    @property
    def sum(self):
        return sum(self.parts)

    def element_at(self, i):
        return self.parts[i]

    def to_row_count_dict(self) -> Dict[int, int]:
        return dict(Counter(self.parts))

    def delete_first_row(self):
        if len(self.parts) <= 1:
            return Partition(())
        return Partition(self.parts[1:])

    def concat(self, other_partition):
        return Partition(self.parts + tuple(other_partition.parts))

    def __repr__(self):
        return f"Partition{self.parts}"

    def __str__(self):
        return str(self.parts)

    def to_key(self):
        return self.parts

    def subpartitions(self) -> Iterator['Partition']:
        """
        Enumerate all partitions tau such that for each part-size s, multiplicity(tau,s) <= multiplicity(self,s).
        I.e., choose for each distinct part size s an integer 0..m_s.
        Returned partitions are normalized (sorted).
        """
        counts = self.to_row_count_dict()
        sizes = list(counts.items())  # list of (size, multiplicity)
        # recursive enumeration
        def rec(i, chosen_mults):
            if i == len(sizes):
                parts = []
                for s, m in chosen_mults:
                    parts.extend([s] * m)
                yield Partition(parts)
            else:
                s, m = sizes[i]
                for take in range(0, m + 1):
                    chosen_mults.append((s, take))
                    yield from rec(i + 1, chosen_mults)
                    chosen_mults.pop()
        yield from rec(0, [])

# -------------------------
# Polynomial (with Fraction)
# -------------------------
class Polynomial:
    def __init__(self, coeffs=None):
        # coeffs: dict degree->Fraction OR list/tuple of coefficients from const->...
        if coeffs is None:
            self.coef = {}  # degree -> Fraction
        elif isinstance(coeffs, dict):
            self.coef = {d: Fraction(c) for d, c in coeffs.items() if Fraction(c) != 0}
        else:
            # assume sequence: [c0, c1, c2, ...]
            self.coef = {}
            for d, c in enumerate(coeffs):
                if Fraction(c) != 0:
                    self.coef[d] = Fraction(c)
        self._clean()

    def _clean(self):
        self.coef = {d: Fraction(c) for d, c in self.coef.items() if Fraction(c) != 0}

    @staticmethod
    def zero():
        return Polynomial({})

    @staticmethod
    def one():
        return Polynomial({0: Fraction(1)})

    def degree(self):
        return max(self.coef.keys()) if self.coef else -1

    def __add__(self, other):
        res = dict(self.coef)
        for d, c in other.coef.items():
            res[d] = res.get(d, Fraction(0)) + c
            if res[d] == 0:
                del res[d]
        return Polynomial(res)

    def __sub__(self, other):
        res = dict(self.coef)
        for d, c in other.coef.items():
            res[d] = res.get(d, Fraction(0)) - c
            if res[d] == 0:
                del res[d]
        return Polynomial(res)

    def __mul__(self, other):
        if not self.coef or not other.coef:
            return Polynomial.zero()
        res = {}
        for d1, c1 in self.coef.items():
            for d2, c2 in other.coef.items():
                dd = d1 + d2
                res[dd] = res.get(dd, Fraction(0)) + c1 * c2
        return Polynomial(res)

    def scalar_multiply(self, r):
        r = Fraction(r)
        if r == 0 or not self.coef:
            return Polynomial.zero()
        return Polynomial({d: c * r for d, c in self.coef.items()})

    def __repr__(self):
        if not self.coef:
            return "0"
        terms = []
        for d in sorted(self.coef.keys()):
            c = self.coef[d]
            if d == 0:
                terms.append(f"{c}")
            elif d == 1:
                terms.append(f"{c}*x")
            else:
                terms.append(f"{c}*x^{d}")
        return " + ".join(terms)

    def involution(self):
        """
        Polynomial involution: replace x with 1/x and multiply by x^degree
        This corresponds to reversing the coefficients
        """
        if not self.coef:
            return Polynomial.zero()
        
        max_deg = max(self.coef.keys())
        new_coef = {}
        for d, c in self.coef.items():
            new_deg = max_deg - d
            new_coef[new_deg] = c
        
        return Polynomial(new_coef)

# -------------------------
# Partition generation: more sophisticated version matching JS
# -------------------------
def generate_partitions_of_n(n: int) -> Iterator[Partition]:
    """Generate all partitions of n in lexicographic order"""
    if n == 0:
        yield Partition([])
    else:
        first_partition = Partition([n])
        yield from dominated_partitions(first_partition)

def dominated_partitions(partition: Partition) -> Iterator[Partition]:
    """Generate all partitions dominated by the given partition in reverse lexicographic order"""
    current_partition = partition
    while current_partition is not None:
        yield current_partition
        current_partition = next_partition(current_partition)

def next_partition(partition: Partition) -> Partition:
    """Get the next partition in reverse lexicographic order"""
    if len(partition) >= 1 and partition.element_at(0) == 1:
        return None
    
    i = len(partition) - 1
    while i >= 0 and partition.element_at(i) == 1:
        i -= 1
    
    if i < 0:
        return None
    
    remove_from_row = i
    new_row_value = partition.element_at(remove_from_row) - 1
    
    # Build new partition
    new_parts = list(partition.parts[:remove_from_row])
    new_parts.append(new_row_value)
    
    # Calculate remaining sum to distribute
    remaining_sum = partition.sum - sum(new_parts)
    
    # Complete partition maximally
    new_parts.extend(complete_partition_maximally(new_row_value, remaining_sum))
    
    return Partition(new_parts)

def complete_partition_maximally(max_first_row: int, length: int) -> List[int]:
    """Complete a partition maximally given constraints"""
    if length == 0:
        return []
    
    quotient = length // max_first_row
    remainder = length % max_first_row
    
    result = [max_first_row] * quotient
    if remainder != 0:
        result.append(remainder)
    
    return result

def generate_partitions(n: int) -> Iterator[Partition]:
    """Generate all partitions of n"""
    return generate_partitions_of_n(n)

# -------------------------
# Remove the old cached centralizer_size function since it's now in Calculator
# -------------------------

# -------------------------
# Calculator implementing Green polynomials (enhanced to match JS structure)
# -------------------------
class Calculator:
    def __init__(self):
        self._factorial_calculator = FactorialCalculator()
        self._binomial_calculator = BinomialCoefficientCalculator()
        self._basic_polynomials: Dict[int, Polynomial] = {}
        self._partition_polynomials: Dict[Tuple[int,...], Polynomial] = {}
        self._centralizer_sizes: Dict[Tuple[int,...], int] = {}
        self._green_polynomials: Dict[Tuple[Tuple[int,...], Tuple[int,...]], Polynomial] = {}
        self._character_tables: Dict[int, object] = {}  # Would need CharacterTable implementation

    def factorial(self, n: int) -> int:
        return self._factorial_calculator.get(n)
    
    def binomial_coefficient(self, n: int, k: int) -> int:
        return self._binomial_calculator.get(n, k)

    def get_basic_polynomial(self, j: int) -> Polynomial:
        if j in self._basic_polynomials:
            return self._basic_polynomials[j]
        
        # Create polynomial: 1 - x^j (coefficients: [1, 0, 0, ..., -1])
        coeffs = [Fraction(1)] + [Fraction(0)] * (j - 1) + [Fraction(-1)]
        p = Polynomial(coeffs)
        self._basic_polynomials[j] = p
        return p

    def centralizer_size(self, cycle_type: Partition) -> int:
        key = cycle_type.to_key()
        if key in self._centralizer_sizes:
            return self._centralizer_sizes[key]
        
        partition = cycle_type
        centralizer_size = 1
        
        for part_size, multiplicity in partition.to_row_count_dict().items():
            centralizer_size *= (part_size ** multiplicity) * self.factorial(multiplicity)
        
        self._centralizer_sizes[key] = centralizer_size
        return centralizer_size

    def z_inverse(self, partition: Partition) -> Polynomial:
        key = partition.to_key()
        if key in self._partition_polynomials:
            return self._partition_polynomials[key]
        
        result = Polynomial.one()
        for part in partition.parts:
            basic_polynomial = self.get_basic_polynomial(part)
            result = result * basic_polynomial
        
        z_lambda = self.centralizer_size(partition)
        result = result.scalar_multiply(Fraction(1, z_lambda))
        
        self._partition_polynomials[key] = result
        return result

    def green_polynomial_Q(self, lam: Partition, mu: Partition) -> Polynomial:
        """Green polynomial with Q-variable (involution of X-version)"""
        polynomial = self.green_polynomial_X(lam, mu)
        return polynomial.involution()

    def green_polynomial_X(self, lam: Partition, mu: Partition) -> Polynomial:
        key = (lam.to_key(), mu.to_key())
        if key in self._green_polynomials:
            return self._green_polynomials[key]

        if lam.sum != mu.sum:
            self._green_polynomials[key] = Polynomial.zero()
            return Polynomial.zero()

        n = lam.sum

        if len(lam) <= 1:
            self._green_polynomials[key] = Polynomial.one()
            return Polynomial.one()

        result = Polynomial.zero()
        
        # Get relevant dominated partitions
        relevant_dominated = [tau for tau in mu.subpartitions() 
                            if tau.sum <= n - lam.element_at(0)]
        
        mu_count = mu.to_row_count_dict()
        
        for tau in relevant_dominated:
            tau_count = tau.to_row_count_dict()
            
            # Calculate binomial product
            binomial_product = 1
            for part_size in mu_count.keys():
                mu_mult = mu_count.get(part_size, 0)
                tau_mult = tau_count.get(part_size, 0)
                binomial_product *= self.binomial_coefficient(mu_mult, tau_mult)
            
            # Generate smaller partitions
            remaining_sum = n - lam.element_at(0) - tau.sum
            for rho in generate_partitions(remaining_sum):
                current_polynomial = self.z_inverse(rho)
                recursive_partition = tau.concat(rho)
                recursive = self.green_polynomial_X(lam.delete_first_row(), recursive_partition)
                
                term_to_add = recursive * current_polynomial
                scalar = Fraction(binomial_product, 1)
                term_to_add = term_to_add.scalar_multiply(scalar)
                
                if len(rho) % 2 == 0:
                    result = result + term_to_add
                else:
                    result = result - term_to_add

        self._green_polynomials[key] = result
        return result

    @staticmethod
    def generate_partitions(n: int) -> Iterator[Partition]:
        """Static method matching the JS version"""
        return generate_partitions(n)

# -------------------------
# JingLiu class (main interface matching JS)
# -------------------------
class JingLiu:
    @staticmethod
    def green_polynomial(lam, mu):
        """Main interface for computing Green polynomials"""
        return Calculator().green_polynomial_X(lam, mu)

# -------------------------
# Public functions
# -------------------------
def green_polynomial(lambda_parts: List[int], mu_parts: List[int]) -> Polynomial:
    """
    Compute the Green polynomial G_mu^lambda(x).
    lambda_parts and mu_parts should be sequences of ints (rows), e.g. [3,1] for partition (3,1).
    Returns a Polynomial (coefficients are Fraction).
    """
    lam = Partition(lambda_parts)
    mu = Partition(mu_parts)
    calc = Calculator()
    return calc.green_polynomial_X(lam, mu)

def green_polynomial_Q(lambda_parts: List[int], mu_parts: List[int]) -> Polynomial:
    """
    Compute the Green polynomial G_mu^lambda(q) with involution.
    """
    lam = Partition(lambda_parts)
    mu = Partition(mu_parts)
    calc = Calculator()
    return calc.green_polynomial_Q(lam, mu)

def green(lambda_parts: List[int]) -> Polynomial:
    """
    Compute the Green polynomial G_{(1^n)}^lambda(x) where n = sum(lambda_parts).
    """
    lam = Partition(lambda_parts)
    n = lam.sum
    mu = Partition([1] * n)
    calc = Calculator()
    return calc.green_polynomial_Q(lam, mu)

def green_eval(lambda_parts: List[int], q) -> int:
    """
    Compute the Green polynomial G_{(1^n)}^lambda(q) where n = sum(lambda_parts), and evaluate it at q.
    """
    lam = Partition(lambda_parts)
    n = lam.sum
    mu = Partition([1] * n)
    calc = Calculator()
    poly = calc.green_polynomial_Q(lam, mu)
    # Evaluate polynomial at q
    result = 0
    for d, c in poly.coef.items():
        result = result + c * (q ** d)
    return result