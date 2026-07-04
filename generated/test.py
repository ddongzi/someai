import random

def grid_random_algorithm(rows, cols):
    # 初始化一个空的网格
    grid = [[0 for _ in range(cols)] for _ in range(rows)]
    
    # 随机填充网格
    for i in range(rows):
        for j in range(cols):
            grid[i][j] = random.randint(1, 100)
    
    return grid

# 示例用法
rows = 5
cols = 5
random_grid = grid_random_algorithm(rows, cols)
for row in random_grid:
    print(row)