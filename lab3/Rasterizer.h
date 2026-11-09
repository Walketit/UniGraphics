#pragma once
#include "Math3D.h"
#include "Geometry.h"
#include "Camera.h"
#include <vector>
#include <algorithm>
#include <cstdint>

// Режимы закраски
enum ShadingMode {
    SHADING_FLAT, // Плоская закраска
    SHADING_PHONG // Закраска по Фонгу
};

// Параметры источника света и материала
struct Light {
    Vec3 pos;       // Позиция источника света в мировых координатах
    float intensity;// Интенсивность источника Il
};

struct Material {
    float Ka; // Коэффициент фонового отражения (ambient)
    float Kd; // Коэффициент диффузного отражения (diffuse)
    float Ks; // Коэффициент зеркального отражения (specular)
    float shininess; // Показатель гладкости поверхности Фонга (степень n/p)
};

// Вершина, спроецированная на экран
struct ScreenVertex {
    Vec3 screenPos; // x, y - пиксели на экране, z - глубина для Z-буфера
    Vec3 worldPos;  // мировые координаты (нужны для расчета вектора на свет и к камере)
    Vec3 normal;    // нормаль в вершине (для сглаживания по Фонгу)
};

class Rasterizer {
public:
    int width;
    int height;
    std::vector<uint32_t> framebuffer; // Пиксели в формате 0x00RRGGBB
    std::vector<float> depthBuffer;    // Z-буфер глубин

    Light light;
    Material material;
    float ambientIntensity; // Ia из лекции

    Rasterizer(int w, int h)
        : width(w), height(h),
          framebuffer(w * h, 0),
          depthBuffer(w * h, 1e9f) {
        
        // Источник света сверху-сбоку
        light.pos = Vec3(5.0f, 6.0f, 8.0f);
        light.intensity = 1.0f;

        // Параметры материала
        material.Ka = 0.2f; // фоновое свечение (чтобы тени не были абсолютно черными)
        material.Kd = 0.65f; // диффузная составляющая (основной матовый свет)
        material.Ks = 0.45f; // зеркальный блик
        material.shininess = 32.0f; // острота блика

        ambientIntensity = 0.8f;
    }

    // Очистка кадрового буфера и Z-буфера
    void clear(uint32_t clearColor = 0x001A1A1A) {
        std::fill(framebuffer.begin(), framebuffer.end(), clearColor);
        std::fill(depthBuffer.begin(), depthBuffer.end(), 1e9f);
    }

    // Перевод точки из пространства NDC [-1, 1] в экранные пиксели
    Vec3 ndcToScreen(const Vec3& ndc) const {
        return Vec3(
            (ndc.x + 1.0f) * 0.5f * (width - 1),
            (1.0f - ndc.y) * 0.5f * (height - 1), // инвертируем Y, так как строки экрана идут сверху вниз
            ndc.z
        );
    }

    // Барицентрические координаты точки P относительно треугольника A, B, C
    static Vec3 barycentric(const Vec3& a, const Vec3& b, const Vec3& c, float px, float py) {
        float denom = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y);
        if (std::abs(denom) < 1e-6f) return Vec3(-1, -1, -1);

        float w0 = ((b.y - c.y) * (px - c.x) + (c.x - b.x) * (py - c.y)) / denom;
        float w1 = ((c.y - a.y) * (px - c.x) + (a.x - c.x) * (py - c.y)) / denom;
        float w2 = 1.0f - w0 - w1;

        return Vec3(w0, w1, w2);
    }

    // Вычисление цвета в оттенках серого
    // Формула: I = Ia * Ka + Il * (Kd * (N · L) + Ks * (R · S)^n)
    uint32_t calculateLightingGrayscale(const Vec3& point, const Vec3& normal, const Vec3& viewPos, bool includeSpecular) const {
        Vec3 N = normal.normalized();
        Vec3 L = (light.pos - point).normalized(); // направление на источник света
        Vec3 S = (viewPos - point).normalized();   // направление на наблюдателя (камеру)

        // Фоновая составляющая (Ambient)
        float ambient = ambientIntensity * material.Ka;

        // Диффузная составляющая (закон Ламберта)
        float nDotL = std::max(0.0f, dot(N, L));
        float diffuse = light.intensity * material.Kd * nDotL;

        // Зеркальная составляющая (модель Фонга)
        float specular = 0.0f;
        if (includeSpecular && nDotL > 0.0f) {
            // Отраженный луч R = 2 * (N · L) * N - L
            Vec3 R = (2.0f * dot(N, L) * N - L).normalized();
            float rDotS = std::max(0.0f, dot(R, S));
            specular = light.intensity * material.Ks * std::pow(rDotS, material.shininess);
        }

        // Суммарная интенсивность
        float I = ambient + diffuse + specular;
        I = std::max(0.0f, std::min(1.0f, I)); // клампинг в диапазон [0, 1]

        // Перевод интенсивности в градации серого: R = G = B
        uint8_t gray = static_cast<uint8_t>(I * 255.0f);
        return (gray << 16) | (gray << 8) | gray;
    }

    // Растеризация одного треугольника с плоской закраской
    void drawTriangleFlat(const ScreenVertex& sv0, const ScreenVertex& sv1, const ScreenVertex& sv2,
                          const Vec3& faceNormal, const Vec3& cameraEye) {
        
        // Вычисляем цвет грани один раз (по формуле освещенности для центра полигона)
        Vec3 faceCenterWorld = (sv0.worldPos + sv1.worldPos + sv2.worldPos) / 3.0f;
        uint32_t flatColor = calculateLightingGrayscale(faceCenterWorld, faceNormal, cameraEye, false);

        // Ограничивающий прямоугольник треугольника (Bounding Box) на экране
        int minX = std::max(0, static_cast<int>(std::floor(std::min({sv0.screenPos.x, sv1.screenPos.x, sv2.screenPos.x}))));
        int maxX = std::min(width - 1, static_cast<int>(std::ceil(std::max({sv0.screenPos.x, sv1.screenPos.x, sv2.screenPos.x}))));
        int minY = std::max(0, static_cast<int>(std::floor(std::min({sv0.screenPos.y, sv1.screenPos.y, sv2.screenPos.y}))));
        int maxY = std::min(height - 1, static_cast<int>(std::ceil(std::max({sv0.screenPos.y, sv1.screenPos.y, sv2.screenPos.y}))));

        if (minX > maxX || minY > maxY) return;

        // Обход пикселей внутри ограничивающего прямоугольника
        for (int y = minY; y <= maxY; ++y) {
            for (int x = minX; x <= maxX; ++x) {
                Vec3 w = barycentric(sv0.screenPos, sv1.screenPos, sv2.screenPos, static_cast<float>(x), static_cast<float>(y));

                // Проверяем, лежит ли точка внутри треугольника
                if (w.x >= 0.0f && w.y >= 0.0f && w.z >= 0.0f) {
                    // Интерполяция глубины для Z-буфера
                    float z = w.x * sv0.screenPos.z + w.y * sv1.screenPos.z + w.z * sv2.screenPos.z;

                    int pixelIndex = y * width + x;
                    // Тест глубины: если пиксель ближе, чем записанный в Z-буфере
                    if (z < depthBuffer[pixelIndex]) {
                        depthBuffer[pixelIndex] = z;
                        framebuffer[pixelIndex] = flatColor; // закрашиваем найденным цветом грани
                    }
                }
            }
        }
    }

    // Отрисовка всей 3D сетки в режиме плоской закраски
    void renderMeshFlat(const Mesh& mesh, const Camera& camera) {
        Mat4 view = camera.getViewMatrix();
        Mat4 proj = camera.getProjectionMatrix();
        Mat4 viewProj = proj * view;

        for (const auto& tri : mesh.triangles) {
            const Vertex& v0 = mesh.vertices[tri.v0];
            const Vertex& v1 = mesh.vertices[tri.v1];
            const Vertex& v2 = mesh.vertices[tri.v2];

            // Проверка отсечение нелицевых граней
            // Вектор взгляда на треугольник от камеры
            Vec3 toTriangle = (v0.pos - camera.eye).normalized();
            if (dot(tri.faceNormal, toTriangle) >= 0.0f) {
                continue; // треугольник отвернут от камеры
            }

            // Трансформируем вершины в экранные координаты
            ScreenVertex sv0, sv1, sv2;

            Vec3 ndc0 = viewProj.transformPoint(v0.pos);
            Vec3 ndc1 = viewProj.transformPoint(v1.pos);
            Vec3 ndc2 = viewProj.transformPoint(v2.pos);

            sv0.screenPos = ndcToScreen(ndc0);
            sv1.screenPos = ndcToScreen(ndc1);
            sv2.screenPos = ndcToScreen(ndc2);

            sv0.worldPos = v0.pos;
            sv1.worldPos = v1.pos;
            sv2.worldPos = v2.pos;

            drawTriangleFlat(sv0, sv1, sv2, tri.faceNormal, camera.eye);
        }
    }

    // Растеризация одного треугольника с закраской по Фонгу
    // Интерполирует вектор нормали в каждый пиксель и считает свет попиксельно
    void drawTrianglePhong(const ScreenVertex& sv0, const ScreenVertex& sv1, const ScreenVertex& sv2,
                           const Vec3& cameraEye) {
        
        // Ограничивающий прямоугольник (Bounding Box)
        int minX = std::max(0, static_cast<int>(std::floor(std::min({sv0.screenPos.x, sv1.screenPos.x, sv2.screenPos.x}))));
        int maxX = std::min(width - 1, static_cast<int>(std::ceil(std::max({sv0.screenPos.x, sv1.screenPos.x, sv2.screenPos.x}))));
        int minY = std::max(0, static_cast<int>(std::floor(std::min({sv0.screenPos.y, sv1.screenPos.y, sv2.screenPos.y}))));
        int maxY = std::min(height - 1, static_cast<int>(std::ceil(std::max({sv0.screenPos.y, sv1.screenPos.y, sv2.screenPos.y}))));

        if (minX > maxX || minY > maxY) return;

        // Обход пикселей
        for (int y = minY; y <= maxY; ++y) {
            for (int x = minX; x <= maxX; ++x) {
                Vec3 w = barycentric(sv0.screenPos, sv1.screenPos, sv2.screenPos, static_cast<float>(x), static_cast<float>(y));

                if (w.x >= 0.0f && w.y >= 0.0f && w.z >= 0.0f) {
                    float z = w.x * sv0.screenPos.z + w.y * sv1.screenPos.z + w.z * sv2.screenPos.z;

                    int pixelIndex = y * width + x;
                    if (z < depthBuffer[pixelIndex]) {
                        depthBuffer[pixelIndex] = z;

                        // Билинейная интерполяция вектора нормали в текущий пиксель
                        Vec3 interpNormal = (w.x * sv0.normal + w.y * sv1.normal + w.z * sv2.normal).normalized();

                        // Интерполяция мировой позиции точки для расчета направления на свет и камеру
                        Vec3 interpWorldPos = w.x * sv0.worldPos + w.y * sv1.worldPos + w.z * sv2.worldPos;

                        // Попиксельный расчет освещения по модели Фонга с зеркальным бликом
                        uint32_t phongColor = calculateLightingGrayscale(interpWorldPos, interpNormal, cameraEye, true);

                        framebuffer[pixelIndex] = phongColor;
                    }
                }
            }
        }
    }

    // Отрисовка всей 3D сетки в режиме закраски по Фонгу
    void renderMeshPhong(const Mesh& mesh, const Camera& camera) {
        Mat4 view = camera.getViewMatrix();
        Mat4 proj = camera.getProjectionMatrix();
        Mat4 viewProj = proj * view;

        for (const auto& tri : mesh.triangles) {
            const Vertex& v0 = mesh.vertices[tri.v0];
            const Vertex& v1 = mesh.vertices[tri.v1];
            const Vertex& v2 = mesh.vertices[tri.v2];

            // Отсечение задних граней
            Vec3 toTriangle = (v0.pos - camera.eye).normalized();
            if (dot(tri.faceNormal, toTriangle) >= 0.0f) {
                continue;
            }

            // Трансформируем вершины в экранные координаты
            ScreenVertex sv0, sv1, sv2;

            Vec3 ndc0 = viewProj.transformPoint(v0.pos);
            Vec3 ndc1 = viewProj.transformPoint(v1.pos);
            Vec3 ndc2 = viewProj.transformPoint(v2.pos);

            sv0.screenPos = ndcToScreen(ndc0);
            sv1.screenPos = ndcToScreen(ndc1);
            sv2.screenPos = ndcToScreen(ndc2);

            sv0.worldPos = v0.pos;
            sv1.worldPos = v1.pos;
            sv2.worldPos = v2.pos;

            // Передаем сглаженные нормали вершин
            sv0.normal = v0.normal;
            sv1.normal = v1.normal;
            sv2.normal = v2.normal;

            drawTrianglePhong(sv0, sv1, sv2, camera.eye);
        }
    }
};
