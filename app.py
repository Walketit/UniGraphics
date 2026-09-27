"""
Модуль визуализирует 3D-проволочную модель
"""

import tkinter as tk
from tkinter import ttk

from model import create_letter_p, create_coordinate_axes
from projections import (
    orthographic_xy_matrix,
    orthographic_xz_matrix,
    orthographic_yz_matrix,
    isometric_matrix,
    perspective_matrix,
    project_point_to_screen,
    project_points_to_screen
)


class GraphicsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №1: Аффинные преобразования и проецирование буквы «П» в 3D")
        self.root.geometry("1150x720")
        self.root.minsize(900, 600)

        # Модели данных
        self.letter = create_letter_p(width=6.0, height=8.0, thickness=1.5, depth=2.0)
        self.axes = create_coordinate_axes(length=9.0)

        # Параметры отображения
        self.scale = 28.0          # масштаб (пикселей на единицу модели)
        self.pan_x = 0.0           # смещение холста по горизонтали
        self.pan_y = 0.0           # смещение холста по вертикали
        self.canvas_width = 800
        self.canvas_height = 680

        # Изометрическая проекция по умолчанию
        self.projection_var = tk.StringVar(value="isometric")

        # Создаем пользовательский интерфейс
        self._build_ui()

        # Первичная отрисовка сцены
        self.redraw()

    def _build_ui(self):
        """
        Создает структуру интерфейса: левая часть - холст canvas,
        правая часть - панель управления и информация
        """
        # Главный контейнер
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель: графический холст canvas
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#18181b",              
            highlightthickness=1,
            highlightbackground="#3f3f46"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Обработка изменения размера окна
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # Правая панель: Управление и информация
        right_panel = ttk.Frame(main_container, width=320)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 5), pady=5)
        right_panel.pack_propagate(False)

        # Блок выбора проекции
        proj_group = ttk.LabelFrame(right_panel, text=" Проекция ", padding=10)
        proj_group.pack(fill=tk.X, pady=(0, 10))

        projections = [
            ("Изометрическая (3D)", "isometric"),
            ("Перспективная (Камера c=30)", "perspective"),
            ("Вид спереди (Орто XY)", "ortho_xy"),
            ("Вид сверху (Орто XZ)", "ortho_xz"),
            ("Вид сбоку (Орто YZ)", "ortho_yz"),
        ]

        for text, val in projections:
            rb = ttk.Radiobutton(
                proj_group,
                text=text,
                value=val,
                variable=self.projection_var,
                command=self.redraw
            )
            rb.pack(anchor=tk.W, pady=3)

        # Блок масштаба отображения
        view_group = ttk.LabelFrame(right_panel, text=" Масштаб отображения ", padding=10)
        view_group.pack(fill=tk.X, pady=(0, 10))

        zoom_btn_frame = ttk.Frame(view_group)
        zoom_btn_frame.pack(fill=tk.X)

        btn_zoom_in = ttk.Button(zoom_btn_frame, text="Увеличить (+)", command=self._zoom_in)
        btn_zoom_in.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 2))

        btn_zoom_out = ttk.Button(zoom_btn_frame, text="Уменьшить (-)", command=self._zoom_out)
        btn_zoom_out.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(2, 0))

        btn_reset_view = ttk.Button(view_group, text="Сбросить масштаб", command=self._reset_view)
        btn_reset_view.pack(fill=tk.X, pady=(5, 0))

        v_count = len(self.letter.vertices)
        e_count = len(self.letter.edges)
        cx, cy, cz = self.letter.get_center()

        # Блок информации о модели
        info_group = ttk.LabelFrame(right_panel, text=" Информация о модели ", padding=10)
        info_group.pack(fill=tk.X, pady=(0, 10))

        self.lbl_object = ttk.Label(info_group, text="Объект: 3D-буква «П»", font=("Arial", 9, "bold"))
        self.lbl_object.pack(anchor=tk.W, pady=2)

        self.lbl_stats = ttk.Label(info_group, text=f"Вершин: {v_count} | Рёбер: {e_count}")
        self.lbl_stats.pack(anchor=tk.W, pady=2)

        self.lbl_center = ttk.Label(info_group, text=f"Центр C: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
        self.lbl_center.pack(anchor=tk.W, pady=2)

        self.lbl_scale = ttk.Label(info_group, text=f"Масштаб: {self.scale:.1f} px/ед")
        self.lbl_scale.pack(anchor=tk.W, pady=2)

        # Легенда осей
        legend_frame = ttk.LabelFrame(right_panel, text=" Оси координат ", padding=10)
        legend_frame.pack(fill=tk.X, pady=(0, 10))

        lbl_x = tk.Label(legend_frame, text="■ Ось X — Красная", fg="#ef4444")
        lbl_x.pack(anchor=tk.W)
        lbl_y = tk.Label(legend_frame, text="■ Ось Y — Зеленая", fg="#22c55e")
        lbl_y.pack(anchor=tk.W)
        lbl_z = tk.Label(legend_frame, text="■ Ось Z — Синяя", fg="#38bdf8")
        lbl_z.pack(anchor=tk.W)

    def _get_current_projection_matrix(self):
        """
        Возвращает матрицу 4x4 для выбранной пользователем проекции.
        """
        proj_type = self.projection_var.get()

        match proj_type:
            case "isometric":
                return isometric_matrix()
            case "perspective":
                return perspective_matrix(c=30.0)
            case "ortho_xy":
                return orthographic_xy_matrix()
            case "ortho_xz":
                return orthographic_xz_matrix()
            case "ortho_yz":
                return orthographic_yz_matrix()
            case _:
                return isometric_matrix()

    def redraw(self):
        """
        Полная перерисовка сцены на холсте:
            Очистка холста
            Получение текущей матрицы проекции
            Отрисовка координатных осей
            Отрисовка буквы
            Отрисовка точки геометрического центра
            Обновление информационной панели
        """
        self.canvas.delete("all")

        # Получаем размеры холста
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 1:
            self.canvas_width = w
        if h > 1:
            self.canvas_height = h

        proj_matrix = self._get_current_projection_matrix()

        # Рисуем координатные оси
        self._draw_axes(proj_matrix)

        # Рисуем букву
        self._draw_letter(proj_matrix)

        # Рисуем геометрический центр буквы
        self._draw_center(proj_matrix)

        # Обновляем текстовые метки
        cx, cy, cz = self.letter.get_center()
        self.lbl_center.config(text=f"Центр C: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
        self.lbl_scale.config(text=f"Масштаб: {self.scale:.1f} px/ед")

    def _draw_axes(self, proj_matrix):
        """
        Отрисовывает координатные оси X,Y,Z
        """
        pts = project_points_to_screen(
            self.axes.vertices,
            proj_matrix,
            self.canvas_width,
            self.canvas_height,
            scale=self.scale,
            pan_x=self.pan_x,
            pan_y=self.pan_y
        )
        o_x, o_y = pts[0]  # начало координат (0, 0, 0)

        # Ось X
        x_end = pts[1]
        self.canvas.create_line(o_x, o_y, x_end[0], x_end[1], fill="#ef4444", width=2, arrow=tk.LAST)
        self.canvas.create_text(x_end[0] + 10, x_end[1], text="X", fill="#ef4444", font=("Arial", 10, "bold"))

        # Ось Y
        y_end = pts[2]
        self.canvas.create_line(o_x, o_y, y_end[0], y_end[1], fill="#22c55e", width=2, arrow=tk.LAST)
        self.canvas.create_text(y_end[0], y_end[1] - 12, text="Y", fill="#22c55e", font=("Arial", 10, "bold"))

        # Ось Z
        z_end = pts[3]
        self.canvas.create_line(o_x, o_y, z_end[0], z_end[1], fill="#38bdf8", width=2, arrow=tk.LAST)
        self.canvas.create_text(z_end[0] + 10, z_end[1] + 10, text="Z", fill="#38bdf8", font=("Arial", 10, "bold"))

    def _draw_letter(self, proj_matrix):
        """
        Отрисовывает 24 ребра буквы
        """
        pts = project_points_to_screen(
            self.letter.vertices,
            proj_matrix,
            self.canvas_width,
            self.canvas_height,
            scale=self.scale,
            pan_x=self.pan_x,
            pan_y=self.pan_y
        )

        for edge_idx, (i, j) in enumerate(self.letter.edges):
            x1, y1 = pts[i]
            x2, y2 = pts[j]

            # Передняя грань
            if edge_idx < 8:
                color = "#dbf838"
                width = 2
            # Задняя грань
            elif edge_idx < 16:
                color = "#9ca701"
                width = 2
            # Продольные ребра
            else:
                color = "#a855f7"
                width = 1

            self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)

        # Точки на вершинах
        for px, py in pts:
            self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#f8fafc", outline="")

    def _draw_center(self, proj_matrix):
        """
        Отрисовывает маркер геометрического центра буквы
        """
        center = self.letter.get_center()
        cx_s, cy_s = project_point_to_screen(
            center,
            proj_matrix,
            self.canvas_width,
            self.canvas_height,
            scale=self.scale,
            pan_x=self.pan_x,
            pan_y=self.pan_y
        )
        
        r = 4
        self.canvas.create_oval(cx_s - r, cy_s - r, cx_s + r, cy_s + r, fill="#ffffff", outline="#eab308")
        self.canvas.create_text(cx_s + 12, cy_s - 8, text="C", fill="#facc15", font=("Arial", 9, "bold"))

    def _zoom_in(self):
        self.scale = min(self.scale * 1.15, 200.0)
        self.redraw()

    def _zoom_out(self):
        self.scale = max(self.scale / 1.15, 5.0)
        self.redraw()

    def _reset_view(self):
        self.scale = 28.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.redraw()

    def _on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height
        self.redraw()


def main():
    root = tk.Tk()
    app = GraphicsApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
