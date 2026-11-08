#pragma once
#include "Math3D.h"

class Camera {
public:
    Vec3 eye;       // Позиция камеры в мировых координатах
    Vec3 target;    // Точка, на которую смотрит камера (центр сцены)
    Vec3 up;        // Вектор «вверх» для ориентации камеры

    // Точки для анимации движения
    Vec3 point1;
    Vec3 point2;

    float fov;      // Угол обзора по вертикали (в радианах)
    float aspect;   // Соотношение сторон экрана (width / height)
    float nearZ;    // Ближняя плоскость отсечения
    float farZ;     // Дальняя плоскость отсечения

    Camera()
        : eye(0.0f, 2.0f, 6.0f),
          target(0.0f, 0.0f, 0.0f),
          up(0.0f, 1.0f, 0.0f),
          point1(-4.0f, 3.0f, 5.0f), // начальная точка движения
          point2(4.0f, -1.0f, 6.0f), // конечная точка движения
          fov(1.04719755f),          // 60 градусов
          aspect(1.33333333f),       // 800 / 600
          nearZ(0.1f),
          farZ(50.0f) {}

    // Интерполяция положения камеры между point1 и point2 по параметру t от 0 до 1
    void setPositionAlongPath(float t) {
        // Ограничиваем t диапазоном [0, 1]
        t = std::max(0.0f, std::min(1.0f, t));
        eye = (1.0f - t) * point1 + t * point2;
    }

    // Построение матрицы вида (LookAt)
    // Переводит координаты из мировой системы в систему координат камеры
    Mat4 getViewMatrix() const {
        // Ось Z камеры направлена от цели к камере
        Vec3 zAxis = (eye - target).normalized();

        // Ось X камеры перпендикулярна вектору вверх и оси Z (вправо)
        Vec3 xAxis = cross(up, zAxis).normalized();

        // Истинная ось Y камеры
        Vec3 yAxis = cross(zAxis, xAxis).normalized();

        Mat4 view = Mat4::identity();

        view.m[0][0] = xAxis.x;
        view.m[0][1] = xAxis.y;
        view.m[0][2] = xAxis.z;
        view.m[0][3] = -dot(xAxis, eye);

        view.m[1][0] = yAxis.x;
        view.m[1][1] = yAxis.y;
        view.m[1][2] = yAxis.z;
        view.m[1][3] = -dot(yAxis, eye);

        view.m[2][0] = zAxis.x;
        view.m[2][1] = zAxis.y;
        view.m[2][2] = zAxis.z;
        view.m[2][3] = -dot(zAxis, eye);

        return view;
    }

    // Построение матрицы перспективной проекции
    // Проецирует видимую пирамиду в нормализованный куб
    Mat4 getProjectionMatrix() const {
        Mat4 proj;
        float tanHalfFov = std::tan(fov * 0.5f);

        proj.m[0][0] = 1.0f / (aspect * tanHalfFov);
        proj.m[1][1] = 1.0f / tanHalfFov;
        proj.m[2][2] = -(farZ + nearZ) / (farZ - nearZ);
        proj.m[2][3] = -(2.0f * farZ * nearZ) / (farZ - nearZ);
        proj.m[3][2] = -1.0f;
        proj.m[3][3] = 0.0f;

        return proj;
    }
};
