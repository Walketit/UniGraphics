#pragma once
#include "Geometry.h"
#include "Curve.h"
#include <vector>

// Генерация полигональной сетки фигуры вращения и триангуляция
inline Mesh createRevolutionSurface(const std::vector<ProfilePoint>& profile, int slices = 36) {
    Mesh mesh;
    const int numProfilePoints = static_cast<int>(profile.size());
    if (numProfilePoints < 2 || slices < 3) {
        return mesh;
    }

    const float twoPi = 6.28318530718f;

    // Генерация вершин
    // Обходим профиль по высоте (i) и вращаем вокруг оси Y на угол theta (j)
    mesh.vertices.resize(numProfilePoints * slices);

    for (int i = 0; i < numProfilePoints; ++i) {
        float r = profile[i].r;
        float y = profile[i].y;

        for (int j = 0; j < slices; ++j) {
            float theta = j * (twoPi / slices);
            float cosT = std::cos(theta);
            float sinT = std::sin(theta);

            // Точка на окружности в плоскости XZ
            Vec3 pos(r * cosT, y, r * sinT);

            int idx = i * slices + j;
            mesh.vertices[idx].pos = pos;
            mesh.vertices[idx].normal = Vec3(0, 0, 0); // заполнится позже усреднением
        }
    }

    // Триангуляция: каждый четырехсторонний сектор разбиваем на 2 треугольника
    // Порядок обхода вершин выбран так, чтобы вектор нормали смотрел наружу
    for (int i = 0; i < numProfilePoints - 1; ++i) {
        for (int j = 0; j < slices; ++j) {
            int nextJ = (j + 1) % slices;

            int v00 = i * slices + j;             // нижняя-левая
            int v10 = (i + 1) * slices + j;       // верхняя-левая
            int v11 = (i + 1) * slices + nextJ;   // верхняя-правая
            int v01 = i * slices + nextJ;         // нижняя-правая

            // Треугольник 1: (v00, v10, v11)
            Triangle t1;
            t1.v0 = v00;
            t1.v1 = v10;
            t1.v2 = v11;
            Vec3 edge1 = mesh.vertices[t1.v1].pos - mesh.vertices[t1.v0].pos;
            Vec3 edge2 = mesh.vertices[t1.v2].pos - mesh.vertices[t1.v0].pos;
            t1.faceNormal = cross(edge1, edge2).normalized();
            mesh.triangles.push_back(t1);

            // Треугольник 2: (v00, v11, v01)
            Triangle t2;
            t2.v0 = v00;
            t2.v1 = v11;
            t2.v2 = v01;
            Vec3 edge3 = mesh.vertices[t2.v1].pos - mesh.vertices[t2.v0].pos;
            Vec3 edge4 = mesh.vertices[t2.v2].pos - mesh.vertices[t2.v0].pos;
            t2.faceNormal = cross(edge3, edge4).normalized();
            mesh.triangles.push_back(t2);
        }
    }

    // Вычисление нормалей в вершинах (усреднение нормалей смежных граней)
    // Необходимо для сглаживания по Фонгу
    for (const auto& tri : mesh.triangles) {
        mesh.vertices[tri.v0].normal += tri.faceNormal;
        mesh.vertices[tri.v1].normal += tri.faceNormal;
        mesh.vertices[tri.v2].normal += tri.faceNormal;
    }

    // Нормализуем полученные усредненные нормали вершин
    for (auto& vertex : mesh.vertices) {
        vertex.normal = vertex.normal.normalized();
    }

    return mesh;
}
