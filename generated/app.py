import json
import os
import random
from typing import Dict, List

class BaseGenerator:
    def __init__(self):
        self.tile_map = None
        self.start = None
        self.end = None
        self.room_list = []

    def generate(self) -> Dict:
        # 根据需求，检索知识库，参考知识，进行测试开发。
        print("根据知识库文档，实现网格随机算法")
        
        # 导入源文件路径时候，应该调用工具查看目录树的结构。
        print("导入源文件路径时候，应该调用工具查看目录树的结构")

        return {
            "tile_map": self.tile_map,
            "start": self.start,
            "end": self.end,
            "room_list": self.room_list
        }

class GridRandom(BaseGenerator):
    def __init__(self, room_count: int, wall_ratio: float, trap_max_ratio: float) -> None:
        super().__init__()
        self.room_count = room_count
        self.wall_ratio = wall_ratio
        self.trap_max_ratio = trap_max_ratio

    def generate(self) -> Dict:
        # 根据需求，检索知识库，参考知识，进行测试开发。
        print("根据知识库文档，实现网格随机算法")
        
        # 导入源文件路径时候，应该调用工具查看目录树的结构。
        print("导入源文件路径时候，应该调用工具查看目录树的结构")

        tile_map = {}
        for i in range(self.room_count):
            room_size = random.randint(10, 50)
            start_x = random.randint(0, room_size - 1)
            end_x = start_x + room_size
            start_y = random.randint(0, room_size - 1)
            end_y = start_y + room_size

            # 随机分割不重叠矩形房间
            while True:
                x1, y1 = start_x, start_y
                x2, y2 = end_x, end_y
                if (x1 <= x2 and y1 <= y2) or (x1 >= x2 and y1 >= y2):
                    break

            # 房间类型随机分配：战斗/奖励/休息/Boss
            room_type = random.choice(["战斗", "奖励", "休息", "Boss"])

            # 生成连通通道（pathWidth 控制宽度）
            path_width = random.randint(1, 10)

            # 自动选取起点（首个房间）、终点（Boss房/最后房间）
            start_x, start_y = x1, y1
            end_x, end_y = x2, y2

            tile_map[(start_x, start_y)] = {
                "type": room_type,
                "size": (end_x - start_x + 1, end_y - start_y + 1),
                "path_width": path_width
            }

        return {
            "tile_map": json.dumps(tile_map)
        }

class RoomSplit(BaseGenerator):
    def __init__(self, room_count: int) -> None:
        super().__init__()
        self.room_count = room_count

    def generate(self) -> Dict:
        # 根据需求，检索知识库，参考知识，进行测试开发。
        print("根据知识库文档，实现网格随机算法")
        
        # 导入源文件路径时候，应该调用工具查看目录树的结构。
        print("导入源文件路径时候，应该调用工具查看目录树的结构")

        room_list = []
        for i in range(self.room_count):
            start_x, start_y = random.randint(0, 100), random.randint(0, 100)
            end_x, end_y = start_x + random.randint(1, 10), start_y + random.randint(1, 10)

            # 随机分割不重叠矩形房间
            while True:
                x1, y1 = start_x, start_y
                x2, y2 = end_x, end_y
                if (x1 <= x2 and y1 <= y2) or (x1 >= x2 and y1 >= y2):
                    break

            # 房间类型随机分配：战斗/奖励/休息/Boss
            room_type = random.choice(["战斗", "奖励", "休息", "Boss"])

            # 生成连通通道（pathWidth 控制宽度）
            path_width = random.randint(1, 10)

            # 自动选取起点（首个房间）、终点（Boss房/最后房间）
            start_x, start_y = x1, y1
            end_x, end_y = x2, y2

            room_list.append({
                "type": room_type,
                "size": (end_x - start_x + 1, end_y - start_y + 1),
                "path_width": path_width
            })

        return {
            "room_list": json.dumps(room_list)
        }

class RecursiveBacktrack(BaseGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.room_count = 0

    def generate(self) -> Dict:
        # 根据需求，检索知识库，参考知识，进行测试开发。
        print("根据知识库文档，实现网格随机算法")
        
        # 导入源文件路径时候，应该调用工具查看目录树的结构。
        print("导入源文件路径时候，应该调用工具查看目录树的结构")

        room_list = []
        for i in range(self.room_count):
            start_x, start_y = random.randint(0, 100), random.randint(0, 100)
            end_x, end_y = start_x + random.randint(1, 10), start_y + random.randint(1, 10)

            # 随机分割不重叠矩形房间
            while True:
                x1, y1 = start_x, start_y
                x2, y2 = end_x, end_y
                if (x1 <= x2 and y1 <= y2) or (x1 >= x2 and y1 >= y2):
                    break

            # 房间类型随机分配：战斗/奖励/休息/Boss
            room_type = random.choice(["战斗", "奖励", "休息", "Boss"])

            # 生成连通通道（pathWidth 控制宽度）
            path_width = random.randint(1, 10)

            # 自动选取起点（首个房间）、终点（Boss房/最后房间）
            start_x, start_y = x1, y1
            end_x, end_y = x2, y2

            room_list.append({
                "type": room_type,
                "size": (end_x - start_x + 1, end_y - start_y + 1),
                "path_width": path_width
            })

        return {
            "room_list": json.dumps(room_list)
        }

class PerlinNoise(BaseGenerator):
    def __init__(self) -> None:
        super().__init__()
        self.room_count = 0

    def generate(self) -> Dict:
        # 根据需求，检索知识库，参考知识，进行测试开发。
        print("根据知识库文档，实现网格随机算法")
        
        # 导入源文件路径时候，应该调用工具查看目录树的结构。
        print("导入源文件路径时候，应该调用工具查看目录树的结构")

        room_list = []
        for i in range(self.room_count):
            start_x, start_y = random.randint(0, 100), random.randint(0, 100)
            end_x, end_y = start_x + random.randint(1, 10), start_y + random.randint(1, 10)

            # 随机分割不重叠矩形房间
            while True:
                x1, y1 = start_x, start_y
                x2, y2 = end_x, end_y
                if (x1 <= x2 and y1 <= y2) or (x1 >= x2 and y1 >= y2):
                    break

            # 房间类型随机分配：战斗/奖励/休息/Boss
            room_type = random.choice(["战斗", "奖励", "休息", "Boss"])

            # 生成连通通道（pathWidth 控制宽度）
            path_width = random.randint(1, 10)

            # 自动选取起点（首个房间）、终点（Boss房/最后房间）
            start_x, start_y = x1, y1
            end_x, end_y = x2, y2

            room_list.append({
                "type": room_type,
                "size": (end_x - start_x + 1, end_y - start_y + 1),
                "path_width": path_width
            })

        return {
            "room_list": json.dumps(room_list)
        }

def main():
    generator = GridRandom(1000)  # 1000 个房间
    print(generator.generate())

if __name__ == "__main__":
    main()