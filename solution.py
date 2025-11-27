def solve():
    n, k = map(int, input().split())
    s = input().strip()

    MOD = 10**9 + 7
    m = len(s)

    # Build prefix function for KMP algorithm
    pi = [0] * m
    for i in range(1, m):
        j = pi[i-1]
        while j > 0 and s[i] != s[j]:
            j = pi[j-1]
        if s[i] == s[j]:
            j += 1
        pi[i] = j

    # Build automaton transition table
    # transition[state][c] = (new_state, is_match)
    transition = [[None] * 26 for _ in range(m)]

    for state in range(m):
        for c_idx in range(26):
            char = chr(ord('a') + c_idx)
            j = state
            while j > 0 and s[j] != char:
                j = pi[j-1]
            if s[j] == char:
                j += 1

            if j == m:
                # Found complete match
                transition[state][c_idx] = (pi[m-1], True)
            else:
                transition[state][c_idx] = (j, False)

    # Dynamic Programming
    # dp[i][state][cnt] = number of strings of length i, in automaton state 'state',
    # with 'cnt' occurrences of substring s
    # Use rolling array to optimize memory
    dp = [[[0] * (k+2) for _ in range(m)] for _ in range(2)]
    dp[0][0][0] = 1

    for i in range(n):
        curr = i % 2
        next_idx = 1 - curr

        # Clear next layer
        for state in range(m):
            for cnt in range(k+2):
                dp[next_idx][state][cnt] = 0

        # Process transitions
        for state in range(m):
            for cnt in range(k+2):
                if dp[curr][state][cnt] == 0:
                    continue

                # Try all possible next characters
                for c_idx in range(26):
                    new_state, is_match = transition[state][c_idx]
                    new_cnt = cnt + (1 if is_match else 0)

                    if new_cnt <= k:
                        dp[next_idx][new_state][new_cnt] = (
                            dp[next_idx][new_state][new_cnt] + dp[curr][state][cnt]
                        ) % MOD

    # Collect answer - all strings of length n with exactly k occurrences
    result = 0
    final = n % 2
    for state in range(m):
        result = (result + dp[final][state][k]) % MOD

    print(result)

if __name__ == "__main__":
    solve()
