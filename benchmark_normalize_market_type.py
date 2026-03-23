import timeit
import re

def original_normalize_market_type(market_type_str: str, symbol: str) -> str:
    lowered_str = str(market_type_str).lower()
    if any(keyword in lowered_str for keyword in ['perp', 'future', 'vadeli', 'swap']):
        return 'future'
    if ':' in symbol or symbol.endswith('-SWAP'):
        return 'future'
    return 'spot'

_FUTURES_KEYWORDS = ('perp', 'future', 'vadeli', 'swap')

def optimized_normalize_market_type(market_type_str: str, symbol: str) -> str:
    # NaN / None protection check would normally go here
    if not market_type_str or str(market_type_str) == 'nan':
        pass # Handle NaN/None in the real code

    lowered_str = str(market_type_str).lower()
    for keyword in _FUTURES_KEYWORDS:
        if keyword in lowered_str:
            return 'future'
    if ':' in symbol or symbol.endswith('-SWAP'):
        return 'future'
    return 'spot'

def optimized_normalize_market_type_any(market_type_str: str, symbol: str) -> str:
    lowered_str = str(market_type_str).lower()
    if any(keyword in lowered_str for keyword in _FUTURES_KEYWORDS):
        return 'future'
    if ':' in symbol or symbol.endswith('-SWAP'):
        return 'future'
    return 'spot'

MARKET_TYPE_REGEX = re.compile(r'perp|future|vadeli|swap')

def optimized_normalize_market_type_regex(market_type_str: str, symbol: str) -> str:
    # Adding NaN/None protection for benchmarking parity
    if market_type_str is None or str(market_type_str) == 'nan':
        if ':' in symbol or symbol.endswith('-SWAP'):
            return 'future'
        return 'spot'

    lowered_str = str(market_type_str).lower()
    if MARKET_TYPE_REGEX.search(lowered_str):
        return 'future'

    if ':' in symbol or symbol.endswith('-SWAP'):
        return 'future'
    return 'spot'


def optimized_normalize_market_type_loop_with_guard(market_type_str: str, symbol: str) -> str:
    if market_type_str is None or str(market_type_str) == 'nan':
        if ':' in symbol or symbol.endswith('-SWAP'):
            return 'future'
        return 'spot'

    lowered_str = str(market_type_str).lower()
    for keyword in _FUTURES_KEYWORDS:
        if keyword in lowered_str:
            return 'future'
    if ':' in symbol or symbol.endswith('-SWAP'):
        return 'future'
    return 'spot'


# Module level variables for timeit globals
test_cases = [
    ("spot", "BTC/USDT"),
    ("future", "BTC/USDT"),
    ("perp", "ETH/USDT"),
    ("vadeli", "XRP/USDT"),
    ("swap", "LTC/USDT"),
    ("unknown", "ADA/USDT:USDT"),
    (None, "SOL/USDT"),
    ("NaN", "DOGE/USDT")
]

def run_benchmark():
    num_iterations = 1_000_000

    # Original implementation
    original_time = timeit.timeit(
        "for mt, sym in test_cases: original_normalize_market_type(mt, sym)",
        globals=globals(),
        number=num_iterations
    )

    # Optimized implementation with any
    optimized_any_time = timeit.timeit(
        "for mt, sym in test_cases: optimized_normalize_market_type_any(mt, sym)",
        globals=globals(),
        number=num_iterations
    )

    # Optimized implementation with direct loop
    optimized_loop_time = timeit.timeit(
        "for mt, sym in test_cases: optimized_normalize_market_type_loop_with_guard(mt, sym)",
        globals=globals(),
        number=num_iterations
    )

    # Optimized implementation with regex
    optimized_regex_time = timeit.timeit(
        "for mt, sym in test_cases: optimized_normalize_market_type_regex(mt, sym)",
        globals=globals(),
        number=num_iterations
    )

    print(f"--- Benchmark Results ({num_iterations} iterations, {len(test_cases)} cases each) ---")
    print(f"Original Time:          {original_time:.6f} seconds")
    print(f"Optimized (Any) Time:   {optimized_any_time:.6f} seconds")
    print(f"Optimized (Loop) Time:  {optimized_loop_time:.6f} seconds")
    print(f"Optimized (Regex) Time: {optimized_regex_time:.6f} seconds")

    if original_time > 0:
        improvement_loop = ((original_time - optimized_loop_time) / original_time) * 100
        improvement_regex = ((original_time - optimized_regex_time) / original_time) * 100
        print(f"\nImprovement (Loop):   {improvement_loop:.2f}% faster than Original")
        print(f"Improvement (Regex):  {improvement_regex:.2f}% faster than Original")

        if optimized_regex_time < optimized_loop_time:
            print(f"🏆 Regex is faster than Loop by {((optimized_loop_time - optimized_regex_time) / optimized_loop_time) * 100:.2f}%")
        else:
            print(f"🏆 Loop is faster than Regex by {((optimized_regex_time - optimized_loop_time) / optimized_regex_time) * 100:.2f}%")


if __name__ == "__main__":
    run_benchmark()
