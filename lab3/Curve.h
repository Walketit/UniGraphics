#pragma once
#include "Math3D.h"
#include <vector>

// Точка образующего профиля
struct ProfilePoint {
    float r; // расстояние от оси вращения (радиус)
    float y; // координата по высоте вдоль оси Y
};

// Функция генерации профиля (ваза)
inline std::vector<ProfilePoint> generateProfileCurve(int numPoints = 40) {
    std::vector<ProfilePoint> profile;
    profile.reserve(numPoints);

    const float minY = -2.0f;
    const float maxY = 2.0f;

    for (int i = 0; i < numPoints; ++i) {
        float t = static_cast<float>(i) / (numPoints - 1); // [0, 1]
        float y = minY + t * (maxY - minY);

        float r = 0.9f + 0.35f * std::sin(1.8f * y) + 0.25f * std::cos(0.9f * y);

        if (r < 0.1f) r = 0.1f; // защита от вырождения в ноль/отрицательный радиус

        profile.push_back({ r, y });
    }
    return profile;
}
