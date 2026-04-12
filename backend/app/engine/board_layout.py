LETTER_SCORES = {
    "A":1,"B":3,"C":4,"Ç":4,"D":3,"E":1,"F":7,"G":5,"Ğ":8,"H":5,
    "I":2,"İ":1,"J":10,"K":1,"L":1,"M":2,"N":1,"O":2,"Ö":7,
    "P":5,"R":1,"S":2,"Ş":4,"T":1,"U":2,"Ü":3,"V":7,"Y":3,"Z":4,"?":0
}


def create_bonus_grid_15():
    size = 15
    g = [[None for _ in range(size)] for _ in range(size)]
    k3 = [(0,2),(0,12),(2,0),(2,14),(12,0),(12,14),(14,2),(14,12)]
    h3 = [(1,1),(1,13),(4,4),(4,10),(10,4),(10,10),(13,1),(13,13)]
    k2 = [(2,7),(3,3),(3,11),(7,2),(7,12),(11,3),(11,11),(12,7)]
    h2 = [
        (0,5),(0,9),(1,6),(1,8),
        (5,0),(5,5),(5,9),(5,14),
        (6,1),(6,6),(6,8),(6,13),
        (8,1),(8,6),(8,8),(8,13),
        (9,0),(9,5),(9,9),(9,14),
        (13,6),(13,8),(14,5),(14,9)
    ]
    for r,c in k3: g[r][c] = "K3"
    for r,c in h3: g[r][c] = "H3"
    for r,c in k2: g[r][c] = "K2"
    for r,c in h2: g[r][c] = "H2"
    g[7][7] = "START"
    return g


def create_bonus_grid_9():
    size = 9
    g = [[None for _ in range(size)] for _ in range(size)]
    k3 = [(0,0),(0,8),(8,0),(8,8)]
    h3 = [(0,4),(2,2),(2,6),(4,0),(4,8),(6,2),(6,6),(8,4)]
    k2 = [(1,1),(1,7),(7,1),(7,7)]
    h2 = [(1,3),(1,5),(3,1),(3,7),(5,1),(5,7),(7,3),(7,5)]
    for r,c in k3: g[r][c] = "K3"
    for r,c in h3: g[r][c] = "H3"
    for r,c in k2: g[r][c] = "K2"
    for r,c in h2: g[r][c] = "H2"
    g[4][4] = "START"
    return g


def get_board_config(board_type: str):
    board_type = (board_type or "15x15").lower()
    if board_type == "9x9":
        return {"size": 9, "bonus_grid": create_bonus_grid_9(), "center": (4, 4)}
    return {"size": 15, "bonus_grid": create_bonus_grid_15(), "center": (7, 7)}
