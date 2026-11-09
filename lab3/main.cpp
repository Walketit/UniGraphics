#include <windows.h>
#include <chrono>
#include <string>
#include "Curve.h"
#include "RevolutionSurface.h"
#include "Camera.h"
#include "Rasterizer.h"

// Глобальные переменные для окна и рендеринга
const int SCREEN_WIDTH = 800;
const int SCREEN_HEIGHT = 600;

Rasterizer g_rasterizer(SCREEN_WIDTH, SCREEN_HEIGHT);
Mesh g_mesh;
Camera g_camera;
bool g_usePhong = true; // По умолчанию включено сглаживание по Фонгу. Пробел переключает на Flat

// Оконная процедура Win32
LRESULT CALLBACK WindowProc(HWND hwnd, UINT uMsg, WPARAM wParam, LPARAM lParam) {
    switch (uMsg) {
    case WM_KEYDOWN:
        if (wParam == VK_SPACE) {
            g_usePhong = !g_usePhong; // Пробел переключает режим закраски
            std::string title = g_usePhong ? "Lab 3: Phong Shading (Сглаживание)" : "Lab 3: Flat Shading (Плоская закраска)";
            SetWindowTextA(hwnd, title.c_str());
        }
        else if (wParam == VK_ESCAPE) {
            PostQuitMessage(0);
        }
        return 0;

    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC hdc = BeginPaint(hwnd, &ps);

        BITMAPINFO bmi = { 0 };
        bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
        bmi.bmiHeader.biWidth = SCREEN_WIDTH;
        bmi.bmiHeader.biHeight = -SCREEN_HEIGHT;
        bmi.bmiHeader.biPlanes = 1;
        bmi.bmiHeader.biBitCount = 32;
        bmi.bmiHeader.biCompression = BI_RGB;

        StretchDIBits(
            hdc,
            0, 0, SCREEN_WIDTH, SCREEN_HEIGHT,
            0, 0, SCREEN_WIDTH, SCREEN_HEIGHT,
            g_rasterizer.framebuffer.data(),
            &bmi,
            DIB_RGB_COLORS,
            SRCCOPY
        );

        EndPaint(hwnd, &ps);
        return 0;
    }

    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcA(hwnd, uMsg, wParam, lParam);
}

int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE, LPSTR, int nCmdShow) {
    // Инициализация геометрии фигуры вращения
    auto profile = generateProfileCurve(35);
    g_mesh = createRevolutionSurface(profile, 36);

    // Регистрация окна Win32
    const char CLASS_NAME[] = "Lab3WindowClass";
    WNDCLASSA wc = { 0 };
    wc.lpfnWndProc = WindowProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);
    RegisterClassA(&wc);

    // Настраиваем размер окна с учетом рамки
    RECT rect = { 0, 0, SCREEN_WIDTH, SCREEN_HEIGHT };
    AdjustWindowRect(&rect, WS_OVERLAPPEDWINDOW, FALSE);

    HWND hwnd = CreateWindowExA(
        0, CLASS_NAME, "Lab 3: Phong Shading (Сглаживание) [Space - переключить на Flat, Esc - выход]",
        WS_OVERLAPPEDWINDOW & ~WS_THICKFRAME & ~WS_MAXIMIZEBOX,
        CW_USEDEFAULT, CW_USEDEFAULT,
        rect.right - rect.left, rect.bottom - rect.top,
        NULL, NULL, hInstance, NULL
    );

    if (!hwnd) return 0;
    ShowWindow(hwnd, nCmdShow);

    auto startTime = std::chrono::high_resolution_clock::now();

    // Главный цикл приложения с анимацией движения камеры
    MSG msg = { 0 };
    while (msg.message != WM_QUIT) {
        if (PeekMessageA(&msg, NULL, 0, 0, PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageA(&msg);
        } else {
            // Расчет времени для плавного движения камеры между 2 точками
            auto currentTime = std::chrono::high_resolution_clock::now();
            float elapsed = std::chrono::duration<float>(currentTime - startTime).count();
            float t = (std::sin(elapsed * 1.2f) + 1.0f) * 0.5f;
            g_camera.setPositionAlongPath(t);

            // Очистка буферов
            g_rasterizer.clear(0x00151515);

            // Отрисовка: Phong или Flat в зависимости от режима
            if (g_usePhong) {
                g_rasterizer.renderMeshPhong(g_mesh, g_camera);
            } else {
                g_rasterizer.renderMeshFlat(g_mesh, g_camera);
            }

            // Запрашиваем перерисовку окна
            InvalidateRect(hwnd, NULL, FALSE);
        }
    }

    return 0;
}
