"""
Модуль трехмерной проволочной модели буквы "П"
"""

from transformations import transform_points


class WireframeModel:
    """
    Класс модели хранит: вершины (текущие и начальные), рёбра + методы трансфорамации
    """
    def __init__(self, vertices, edges):
        # Базовые исходные координаты
        self.initial_vertices = [tuple(v) for v in vertices]
        # Текущие трансформированные координаты вершин
        self.vertices = [tuple(v) for v in vertices]
        # Список ребер
        self.edges = list(edges)

    def get_center(self):
        """
        Вычисляет геометрический центр модели:
        C = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
        """
        if not self.vertices:
            return (0.0, 0.0, 0.0)

        xs = [v[0] for v in self.vertices]
        ys = [v[1] for v in self.vertices]
        zs = [v[2] for v in self.vertices]

        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        cz = (min(zs) + max(zs)) / 2.0

        return (cx, cy, cz)

    def apply_matrix(self, matrix):
        """
        Применяет матрицу преобразования к текущим координатам вершин
        """
        self.vertices = transform_points(self.vertices, matrix)

    def reset(self):
        """
        Возвращает вершины модели в исходное состояние
        """
        self.vertices = [tuple(v) for v in self.initial_vertices]


def create_letter_p(width=6.0, height=8.0, thickness=1.5, depth=2.0):
    """
    Генерирует 3D-проволочную модель буквы "П",
    центрированную в начале координат (0, 0, 0)

    Параметры:
      width - общая ширина буквы
      height - общая высота буквы
      thickness - толщина вертикальных стоек и верхней перекладины
      depth - глубина буквы (толщина по оси Z)
    """
    w2 = width / 2.0
    h2 = height / 2.0
    d2 = depth / 2.0

    inner_left = -w2 + thickness
    inner_right = w2 - thickness
    inner_top = h2 - thickness
    bottom = -h2

    # 8 точек 2D-контура буквы "П" (обход по часовой стрелке)
    contour_2d = [
        (-w2, bottom),         # 0: низ левой ноги (снаружи)
        (-w2, h2),             # 1: верх левой ноги (снаружи)
        (w2, h2),              # 2: верх правой ноги (снаружи)
        (w2, bottom),          # 3: низ правой ноги (снаружи)
        (inner_right, bottom), # 4: низ правой ноги (внутри)
        (inner_right, inner_top), # 5: верх проема справа
        (inner_left, inner_top),  # 6: верх проема слева
        (inner_left, bottom),  # 7: низ левой ноги (внутри)
    ]

    # Создаем 16 3D-вершин
    # 0..7 - передняя грань
    # 8..15 - задняя грань
    vertices = []
    for x, y in contour_2d:
        vertices.append((x, y, d2))
    for x, y in contour_2d:
        vertices.append((x, y, -d2))

    # Создаем 24 ребра
    edges = []

    # Ребра передней грани
    for i in range(8):
        next_i = (i + 1) % 8
        edges.append((i, next_i))

    # Ребра задней грани
    for i in range(8):
        next_i = (i + 1) % 8
        edges.append((i + 8, next_i + 8))

    # Соединительные ребра между передней и задней гранями
    for i in range(8):
        edges.append((i, i + 8))

    return WireframeModel(vertices, edges)


def create_coordinate_axes(length=10.0):
    """
    Создает модель 3D координатных осей:
    Ось X: от (0,0,0) до (length, 0, 0)
    Ось Y: от (0,0,0) до (0, length, 0)
    Ось Z: от (0,0,0) до (0, 0, length)
    """
    vertices = [
        (0.0, 0.0, 0.0),     
        (length, 0.0, 0.0),   
        (0.0, length, 0.0),    
        (0.0, 0.0, length)    
    ]
    edges = [
        (0, 1),  
        (0, 2), 
        (0, 3)   
    ]
    return WireframeModel(vertices, edges)
