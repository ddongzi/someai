import random

def grid_random_algorithm(rows, cols):
    # 初始化一个空的网格
    grid = [['.' for _ in range(cols)] for _ in range(rows)]
    
    # 随机选择一个起点
    start_row = random.randint(0, rows - 1)
    start_col = random.randint(0, cols - 1)
    grid[start_row][start_col] = 'S'
    
    # 定义随机移动的方向（上下左右）
    directions = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    
    # 随机生成路径
    path = []
    current_row, current_col = start_row, start_col
    
    while True:
        # 随机选择一个方向
        direction = random.choice(directions)
        
        # 计算新的位置
        new_row, new_col = current_row + direction[0], current_col + direction[1]
        
        # 检查新位置是否在网格范围内且未被访问过
        if 0 <= new_row < rows and 0 <= new_col < cols and grid[new_row][new_col] == '.':
            path.append((current_row, current_col))
            grid[current_row][current_col] = 'P'
            current_row, current_col = new_row, new_col
        
        # 如果路径长度达到网格大小的平方，结束
        if len(path) >= rows * cols:
            break
    
    return grid, path

# 示例用法
rows = 5
cols = 5
grid, path = grid_random_algorithm(rows, cols)
for row in grid:
    print(' '.join(row))
print("Path:", path)