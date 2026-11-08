#pragma once
#include <cmath>
#include <algorithm>

// Трехмерный вектор
struct Vec3 {
    float x, y, z;

    Vec3() : x(0.0f), y(0.0f), z(0.0f) {}
    Vec3(float x, float y, float z) : x(x), y(y), z(z) {}

    Vec3 operator+(const Vec3& v) const { return Vec3(x + v.x, y + v.y, z + v.z); }
    Vec3 operator-(const Vec3& v) const { return Vec3(x - v.x, y - v.y, z - v.z); }
    Vec3 operator*(float s) const { return Vec3(x * s, y * s, z * s); }
    Vec3 operator/(float s) const { return Vec3(x / s, y / s, z / s); }

    Vec3& operator+=(const Vec3& v) {
        x += v.x; y += v.y; z += v.z;
        return *this;
    }

    float length() const {
        return std::sqrt(x * x + y * y + z * z);
    }

    Vec3 normalized() const {
        float len = length();
        if (len > 1e-6f) {
            return *this / len;
        }
        return Vec3(0.0f, 0.0f, 0.0f);
    }
};

inline Vec3 operator*(float s, const Vec3& v) {
    return v * s;
}

// Скалярное произведение
inline float dot(const Vec3& a, const Vec3& b) {
    return a.x * b.x + a.y * b.y + a.z * b.z;
}

// Векторное произведение
inline Vec3 cross(const Vec3& a, const Vec3& b) {
    return Vec3(
        a.y * b.z - a.z * b.y,
        a.z * b.x - a.x * b.z,
        a.x * b.y - a.y * b.x
    );
}

// Матрица 4x4 для преобразований
struct Mat4 {
    float m[4][4];

    Mat4() {
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j)
                m[i][j] = 0.0f;
    }

    static Mat4 identity() {
        Mat4 res;
        for (int i = 0; i < 4; ++i)
            res.m[i][i] = 1.0f;
        return res;
    }

    Mat4 operator*(const Mat4& o) const {
        Mat4 res;
        for (int i = 0; i < 4; ++i) {
            for (int j = 0; j < 4; ++j) {
                float sum = 0.0f;
                for (int k = 0; k < 4; ++k) {
                    sum += m[i][k] * o.m[k][j];
                }
                res.m[i][j] = sum;
            }
        }
        return res;
    }

    // Умножение матрицы на точку (с перспективным делением на w)
    Vec3 transformPoint(const Vec3& p) const {
        float x = m[0][0] * p.x + m[0][1] * p.y + m[0][2] * p.z + m[0][3];
        float y = m[1][0] * p.x + m[1][1] * p.y + m[1][2] * p.z + m[1][3];
        float z = m[2][0] * p.x + m[2][1] * p.y + m[2][2] * p.z + m[2][3];
        float w = m[3][0] * p.x + m[3][1] * p.y + m[3][2] * p.z + m[3][3];

        if (std::abs(w) > 1e-6f) {
            return Vec3(x / w, y / w, z / w);
        }
        return Vec3(x, y, z);
    }

    // Умножение матрицы на вектор направления (без переноса)
    Vec3 transformVector(const Vec3& v) const {
        return Vec3(
            m[0][0] * v.x + m[0][1] * v.y + m[0][2] * v.z,
            m[1][0] * v.x + m[1][1] * v.y + m[1][2] * v.z,
            m[2][0] * v.x + m[2][1] * v.y + m[2][2] * v.z
        );
    }
};
