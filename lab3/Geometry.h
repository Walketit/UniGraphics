#pragma once
#include "Math3D.h"
#include <vector>

// Вершина полигональной сетки
struct Vertex {
    Vec3 pos;       // Координаты вершины в 3D
    Vec3 normal;    // Нормаль в вершине (для сглаживания по Фонгу)
};

// Треугольник с индексами вершин
struct Triangle {
    int v0, v1, v2;
    Vec3 faceNormal;// Нормаль к плоскости треугольника (для плоской закраски)
};

// Полигональная сетка объекта
struct Mesh {
    std::vector<Vertex> vertices;
    std::vector<Triangle> triangles;
};
