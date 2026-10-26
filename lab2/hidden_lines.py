"""
Модуль удаления невидимых граней и рёбер выпуклого многогранника
(Метод внешних нормалей / алгоритм Робертса)
"""

import math


def compute_outward_normal(face_points, body_center):
    """
    Вычисляет вектор внешней нормали N = (nx, ny, nz) для плоской грани:
    1. Находит векторное произведение двух смежных рёбер грани: N = (P1 - P0) x (P2 - P0)
    2. Проверяет ориентацию нормали относительно центра выпуклого тела C:
    если скалярное произведение N * (P0 - C) < 0, разворачивает нормаль наружу
    """
    p0, p1, p2 = face_points[0], face_points[1], face_points[2]

    # Векторы двух сторон грани из вершины P0
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]

    # Векторное произведение u x v
    nx = uy * vz - uz * vy
    ny = uz * vx - ux * vz
    nz = ux * vy - uy * vx

    # Вектор от центра тяжести тела C к вершине грани P0 (направлен наружу)
    wx = p0[0] - body_center[0]
    wy = p0[1] - body_center[1]
    wz = p0[2] - body_center[2]

    # Если нормаль направлена внутрь тела — инвертируем её
    if (nx * wx + ny * wy + nz * wz) < 0.0:
        nx, ny, nz = -nx, -ny, -nz

    return (nx, ny, nz)


def get_view_vector(proj_type, face_point=(0.0, 0.0, 0.0), c=30.0):
    """
    Возвращает вектор направления на наблюдателя S = (sx, sy, sz)
    для выбранного типа проекции
    """
    if proj_type == "isometric":
        # В изометрии (psi = -45°, phi = arcsin(1/sqrt(3))) луч к наблюдателю
        # направлен вдоль биссектрисы первого октанта
        inv_sqrt3 = 1.0 / math.sqrt(3.0)
        return (inv_sqrt3, inv_sqrt3, inv_sqrt3)

    if proj_type == "cabinet":
        # Косоугольная кабинетная проекция (угол 45°, коэффициент 0.5)
        rad = math.radians(45.0)
        dx = -0.5 * math.cos(rad)
        dy = -0.5 * math.sin(rad)
        return (-dx, -dy, 1.0)

    if proj_type == "perspective":
        # Камера расположена на оси Z в точке (0, 0, c)
        return (-face_point[0], -face_point[1], c - face_point[2])

    # Ортогональная проекция на плоскость XY (вид спереди вдоль оси Z)
    return (0.0, 0.0, 1.0)


def classify_model_visibility(model, proj_type="isometric", c=30.0):
    """
    Определяет видимые грани и разделяет рёбра выпуклого тела
    на видимые и невидимые по критерию (N * S) > 0.

    Возвращает словарь:
    visible_faces: список видимых граней (кортежей индексов вершин)
    visible_edges: список видимых рёбер (u, v)
    hidden_edges: список невидимых рёбер (u, v)
    """
    body_center = model.get_center()
    visible_faces = []
    visible_edge_set = set()

    for face in model.faces:
        face_points = [model.vertices[idx] for idx in face]

        # Внешняя нормаль к грани
        nx, ny, nz = compute_outward_normal(face_points, body_center)

        # Центр грани для расчёта луча зрения в перспективе
        m = len(face_points)
        fc = (
            sum(p[0] for p in face_points) / m,
            sum(p[1] for p in face_points) / m,
            sum(p[2] for p in face_points) / m,
        )

        # Вектор взгляда к наблюдателю
        sx, sy, sz = get_view_vector(proj_type, fc, c=c)

        # Скалярное произведение (N * S): если > 0, грань лицевая
        dot_product = nx * sx + ny * sy + nz * sz
        if dot_product > 1e-9:
            visible_faces.append(face)
            for k in range(m):
                u, v = face[k], face[(k + 1) % m]
                visible_edge_set.add((min(u, v), max(u, v)))

    visible_edges = []
    hidden_edges = []
    for u, v in model.edges:
        edge_key = (min(u, v), max(u, v))
        if edge_key in visible_edge_set:
            visible_edges.append((u, v))
        else:
            hidden_edges.append((u, v))

    return {
        "visible_faces": visible_faces,
        "visible_edges": visible_edges,
        "hidden_edges": hidden_edges,
    }
