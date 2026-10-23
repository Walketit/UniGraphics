"""
Модуль проецирования 3D-точек на 2D-плоскость экрана
Реализует виды проецирования:
Ортогональные проекции (XY, XZ, YZ)
Изометрическая проекция
Перспективная проекция

Преобразование видового окна (математические координаты -> экранные пиксели)
"""

import math
from transformations import (
    rotation_x_matrix,
    rotation_y_matrix,
    multiply_matrices,
    transform_point_cartesian
)


def orthographic_xy_matrix():
    """
    Матрица ортогональной проекции на плоскость XY
    """
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]


def orthographic_xz_matrix():
    """
    Матрица ортогональной проекции на плоскость XZ
    """
    return [
        [1.0,  0.0, 0.0, 0.0],
        [0.0,  0.0, 0.0, 0.0],
        [0.0, -1.0, 0.0, 0.0],
        [0.0,  0.0, 0.0, 1.0]
    ]


def orthographic_yz_matrix():
    """
    Матрица ортогональной проекции на плоскость YZ
    """
    return [
        [ 0.0, 0.0, 0.0, 0.0],
        [ 0.0, 1.0, 0.0, 0.0],
        [-1.0, 0.0, 0.0, 0.0],
        [ 0.0, 0.0, 0.0, 1.0]
    ]


def cabinet_matrix(angle_deg=45.0, factor=0.5):
    """
    Матрица кабинетной косоугольной проекции:
      Ось X направлена вправо (горизонтально, масштаб 1:1).
      Ось Y направлена вверх (вертикально, масштаб 1:1).
      Ось Z направлена влево-вниз под углом 45°
      с сокращением масштаба вдвое (factor = 0.5):
      x* = x - factor * cos(angle) * z
      y* = y - factor * sin(angle) * z
    """
    rad = math.radians(angle_deg)
    dx = -factor * math.cos(rad)
    dy = -factor * math.sin(rad)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [ dx,  dy, 0.0, 0.0],
        [0.0, 0.0, 0.0, 1.0]
    ]


def isometric_matrix():
    """
    Матрица изометрической проекции
    Получается последовательностью:
    1. Поворот вокруг оси Y на угол psi = 45 градусов (sin^2(psi) = 1/2)
    2. Поворот вокруг оси X на угол phi = arcsin(1/sqrt(3))
    3. Ортогональное проецирование на плоскость XY
    """
    psi = math.radians(-45.0)                      
    phi = math.asin(1.0 / math.sqrt(3.0))          

    r_y = rotation_y_matrix(psi)
    r_x = rotation_x_matrix(phi)
    p_xy = orthographic_xy_matrix()

    return multiply_matrices(r_y, r_x, p_xy)


def perspective_matrix(c=30.0):
    """
    Матрица перспективной проекции
    """
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 0.0, -1.0 / c],
        [0.0, 0.0, 0.0, 1.0]
    ]


def project_point_to_screen(point, projection_matrix, canvas_width, canvas_height, scale=25.0, pan_x=0.0, pan_y=0.0):
    """
    Проецирования одной 3D-точки на 2D-экран:
    1. Применяет матрицу проекции и делит на w*
    2. Преобразует математические мировые координаты (x_proj, y_proj) в экранные пиксели:
        Центр математических координат (0, 0) помещается в центр холста (width/2, height/2)
        Ось Y инвертируется (в математике вверх, на экране вниз)
        Учитывается масштаб (scale) и панорамирование (pan_x, pan_y)
    """
    # 3D-точка после проецирования в декартовых координатах (x_p, y_p, z_p)
    x_p, y_p, _ = transform_point_cartesian(point, projection_matrix)

    # Перевод в пиксели экрана
    screen_x = (canvas_width / 2.0) + (x_p + pan_x) * scale
    screen_y = (canvas_height / 2.0) - (y_p + pan_y) * scale

    return (screen_x, screen_y)


def project_points_to_screen(points, projection_matrix, canvas_width, canvas_height, scale=25.0, pan_x=0.0, pan_y=0.0):
    """
    Преобразует список 3D-точек в список 2D экранных пикселей
    """
    return [
        project_point_to_screen(pt, projection_matrix, canvas_width, canvas_height, scale, pan_x, pan_y)
        for pt in points
    ]
