"""
Модуль трехмерной полигональной модели выпуклого многогранника
"""

from transformations import transform_points


class WireframeModel:
    """
    Класс модели хранит: вершины (текущие и начальные), рёбра, грани + методы трансформации
    """
    def __init__(self, vertices, edges, faces=None):
        # Базовые исходные координаты
        self.initial_vertices = [tuple(v) for v in vertices]
        # Текущие трансформированные координаты вершин
        self.vertices = [tuple(v) for v in vertices]
        # Список ребер
        self.edges = list(edges)
        # Список граней (многоугольников)
        self.faces = list(faces) if faces is not None else []

    def get_center(self):
        """
        Вычисляет геометрический центр модели как среднее арифметическое вершин:
        C = (sum(x) / N, sum(y) / N, sum(z) / N)
        """
        if not self.vertices:
            return (0.0, 0.0, 0.0)

        n = len(self.vertices)
        cx = sum(v[0] for v in self.vertices) / n
        cy = sum(v[1] for v in self.vertices) / n
        cz = sum(v[2] for v in self.vertices) / n

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


def create_convex_polyhedron():
    """
    Генерирует выпуклый многогранник из 6 многоугольников — усечённую треугольную призму:
      - 2 треугольные грани (3 стороны)
      - 2 четырёхугольные грани (4 стороны)
      - 2 пятиугольные грани (5 сторон)
    """
    vertices = [
        (-3.5, -3.0, -2.5),  # 0: нижняя левая задняя
        ( 3.5, -3.0, -2.5),  # 1: нижняя правая задняя
        ( 0.0, -3.0,  3.5),  # 2: нижняя передняя
        (-3.5,  3.0, -2.5),  # 3: верхняя левая задняя
        ( 3.5,  3.0, -2.5),  # 4: верхняя правая задняя
        (-1.75, 3.0,  0.5),  # 5: верхняя левая точка скоса
        ( 1.75, 3.0,  0.5),  # 6: верхняя правая точка скоса
        ( 0.0,  0.0,  3.5),  # 7: передняя точка скоса
    ]

    # 6 граней (обход вершин против часовой стрелки при взгляде снаружи)
    faces = [
        (0, 1, 2),           # Нижнее основание (треугольник — 3 стороны)
        (5, 7, 6),           # Передний верхний скос (треугольник — 3 стороны)
        (0, 3, 4, 1),        # Задняя грань (четырёхугольник — 4 стороны)
        (3, 5, 6, 4),        # Верхняя грань (четырёхугольник — 4 стороны)
        (0, 2, 7, 5, 3),     # Левая боковая грань (пятиугольник — 5 сторон)
        (1, 4, 6, 7, 2),     # Правая боковая грань (пятиугольник — 5 сторон)
    ]

    # Собираем все 12 уникальных рёбер из граней
    edges = []
    seen = set()
    for face in faces:
        n = len(face)
        for k in range(n):
            u, v = face[k], face[(k + 1) % n]
            edge_key = (min(u, v), max(u, v))
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append(edge_key)

    return WireframeModel(vertices, edges, faces)


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
