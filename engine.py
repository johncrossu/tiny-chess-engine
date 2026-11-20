import json, os, sys, urllib.request

# Configuration
ENV_URL = os.environ["MAKEFUN_ENV_URL"]

# Piece values
V = {'P': 100, 'N': 320, 'B': 330, 'R': 500, 'Q': 900, 'K': 20000}

# Piece-Square Tables (PST)
PST = {
    'P': (0,0,0,0,0,0,0,0, 5,10,10,-20,-20,10,10,5, 5,-5,-10,0,0,-10,-5,5, 0,0,0,20,20,0,0,0, 5,5,10,25,25,10,5,5, 10,10,20,30,30,20,10,10, 50,50,50,50,50,50,50,50, 0,0,0,0,0,0,0,0),
    'N': (-50,-40,-30,-30,-30,-30,-40,-50, -40,-20,0,5,5,0,-20,-40, -30,5,10,15,15,10,5,-30, -30,0,15,20,20,15,0,-30, -30,5,15,20,20,15,5,-30, -30,0,10,15,15,10,0,-30, -40,-20,0,0,0,0,-20,-40, -50,-40,-30,-30,-30,-30,-40,-50),
    'B': (-20,-10,-10,-10,-10,-10,-10,-20, -10,5,0,0,0,0,5,-10, -10,10,10,10,10,10,10,-10, -10,0,10,10,10,10,0,-10, -10,5,5,10,10,5,5,-10, -10,0,5,10,10,0,5,-10, -10,0,0,0,0,0,0,-10, -20,-10,-10,-10,-10,-10,-10,-20),
    'R': (0,0,0,5,5,0,0,0, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, -5,0,0,0,0,0,0,-5, 5,10,10,10,10,10,10,5, 0,0,0,0,0,0,0,0),
    'Q': (-20,-10,-10,-5,-5,-10,-10,-20, -10,0,5,0,0,0,0,-10, -10,5,5,5,5,5,0,-10, 0,0,5,5,5,5,0,-5, -5,0,5,5,5,5,0,-5, -10,0,5,5,5,5,0,-10, -10,0,0,0,0,0,0,-10, -20,-10,-10,-5,-5,-10,-10,-20),
    'K': (20,30,10,0,0,10,30,20, 20,20,0,0,0,0,20,20, -10,-20,-20,-20,-20,-20,-20,-10, -20,-30,-30,-40,-40,-30,-30,-20, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30, -30,-40,-40,-50,-50,-40,-40,-30)
}

# Directions for movement
D = {
    'N': (19, 21, 8, 12, -19, -21, -8, -12),
    'B': (9, 11, -9, -11),
    'R': (1, 10, -1, -10),
    'Q': (1, 10, -1, -10, 9, 11, -9, -11),
    'K': (1, 10, -1, -10, 9, 11, -9, -11)
}

def post(path, body):
    req = urllib.request.Request(ENV_URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)

def parse(fen):
    board = [0] * 120
    for i in range(120):
        if i < 21 or i > 98 or i % 10 == 0 or i % 10 == 9: board[i] = -1
    parts = fen.split()
    rows = parts[0].split('/')
    for r, row in enumerate(rows):
        c = 0
        for char in row:
            if char.isdigit(): c += int(char)
            else: board[21 + r * 10 + c] = char; c += 1
    return board, parts[1] == 'w'

def evaluate(board):
    score = 0
    for i in range(21, 99):
        p = board[i]
        if p == 0 or p == -1: continue
        pt = p.upper()
        v = V[pt]
        r, c = (i // 10) - 2, (i % 10) - 1
        # Piece-square value
        ps = PST[pt][r * 8 + c] if p.isupper() else PST[pt][(7 - r) * 8 + c]
        if p.isupper(): score += v + ps
        else: score -= (v + ps)
    return score

def get_moves(board, white):
    moves_list = []
    for i in range(21, 99):
        p = board[i]
        if p == 0 or p == -1 or p.isupper() != white: continue
        pt = p.upper()
        if pt == 'P':
            d = -10 if white else 10
            # Advance
            if board[i + d] == 0:
                moves_list.append((i, i + d))
                if (white and i > 80) or (not white and i < 40):
                    if board[i + 2 * d] == 0: moves_list.append((i, i + 2 * d))
            # Capture
            for c in [d - 1, d + 1]:
                target = board[i + c]
                if target != 0 and target != -1 and target.isupper() != white:
                    moves_list.append((i, i + c))
        else:
            for dr in D[pt]:
                j = i + dr
                while True:
                    target = board[j]
                    if target == -1: break
                    if target == 0:
                        moves_list.append((i, j))
                        if pt in 'NK': break
                        j += dr
                    else:
                        if target.isupper() != white: moves_list.append((i, j))
                        break
    return moves_list

def search(board, depth, alpha, beta, white):
    if depth == 0: return evaluate(board)
    mvs = get_moves(board, white)
    if not mvs: return evaluate(board)
    # Basic move ordering: captures first
    mvs.sort(key=lambda m: -V[board[m[1]].upper()] if board[m[1]] != 0 and board[m[1]] != -1 else 0)
    
    if white:
        v = -1000000
        for m in mvs:
            old_src, old_dst = board[m[0]], board[m[1]]
            board[m[1]], board[m[0]] = board[m[0]], 0
            v = max(v, search(board, depth - 1, alpha, beta, False))
            board[m[0]], board[m[1]] = old_src, old_dst
            alpha = max(alpha, v)
            if beta <= alpha: break
        return v
    else:
        v = 1000000
        for m in mvs:
            old_src, old_dst = board[m[0]], board[m[1]]
            board[m[1]], board[m[0]] = board[m[0]], 0
            v = min(v, search(board, depth - 1, alpha, beta, True))
            board[m[0]], board[m[1]] = old_src, old_dst
            beta = min(beta, v)
            if beta <= alpha: break
        return v

def uci_to_idx(s):
    return (8 - int(s[1])) * 10 + ord(s[0]) - 97 + 21

def choose(fen, legal):
    board, white = parse(fen)
    best_v = -1000000 if white else 1000000
    best_m = legal[0]
    for uci in legal:
        i, j = uci_to_idx(uci[:2]), uci_to_idx(uci[2:4])
        old_i, old_j = board[i], board[j]
        board[j], board[i] = board[i], 0
        # Handle promotion at root
        if len(uci) == 5:
            board[j] = uci[4].upper() if white else uci[4].lower()
        v = search(board, 2, -1000000, 1000000, not white)
        board[i], board[j] = old_i, old_j
        if white:
            if v > best_v: best_v, best_m = v, uci
        else:
            if v < best_v: best_v, best_m = v, uci
    return best_m

while True:
    g = post("/game", {})
    if g["status"] == "done": break
    while g["status"] == "your_move":
        g = post("/move", {"game": g["game"], "move": choose(g["fen"], g["legal_moves"])})
    print(f"game {g['game']}: {g['outcome']} ({g['reason']})", file=sys.stderr)
