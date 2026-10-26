"""
Главный модуль Лабораторной работы №2 — визуализирует выпуклый многогранник
(6 граней от 3 до 5 сторон) и реализует алгоритм удаления невидимых рёбер
в динамике (при вращении и перемещении).
"""

import math
import tkinter as tk
from tkinter import ttk

from model import create_convex_polyhedron, create_coordinate_axes
from hidden_lines import classify_model_visibility
from transformations import (
    translation_matrix,
    scaling_matrix,
    rotation_around_center_matrix,
    multiply_matrices
)
from projections import (
    orthographic_xy_matrix,
    cabinet_matrix,
    isometric_matrix,
    perspective_matrix,
    project_point_to_screen,
    project_points_to_screen
)


class GraphicsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №2: Удаление невидимых рёбер у выпуклого тела в динамике")
        self.root.geometry("1220x780")
        self.root.minsize(950, 650)

        # Модели выпуклого многогранника и координатных осей
        self.model = create_convex_polyhedron()
        self.axes = create_coordinate_axes(length=9.0)

        # Параметры отображения
        self.scale = 28.0          # масштаб (пикселей на единицу модели)
        self.pan_x = 0.0           # смещение холста по горизонтали
        self.pan_y = 0.0           # смещение холста по вертикали
        self.canvas_width = 800
        self.canvas_height = 700

        # Текущая выбранная проекция
        self.projection_var = tk.StringVar(value="isometric")

        # Режим отображения невидимых линий
        self.vis_mode_var = tk.StringVar(value="hidden_removed")

        # Отображение векторов внешних нормалей граней
        self.show_normals = True
        self.normals_var = tk.BooleanVar(value=True)
        self.step_face_idx = None  # None — сброс, 0..5 — номер текущей проверяемой грани

        # Текст последнего действия
        self.last_action_text = "Готов к управлению"

        # Параметры анимации (вращение в динамике)
        self.is_animating = False
        self.anim_rot_axis_var = tk.StringVar(value="Y")
        self.anim_speed_rot = math.radians(2.5)   # шаг угла вращения за кадр

        # Отображение координатной сетки на плоскости XZ
        self.show_grid = True
        self.grid_var = tk.BooleanVar(value=True)

        # Создаем пользовательский интерфейс
        self._build_ui()

        # Привязка клавиатурных событий ко всему окну
        self.root.bind("<Key>", self._on_key_press)
        self.root.focus_set()

        # Первичная отрисовка сцены
        self.redraw()

    def _build_ui(self):
        """
        Создает структуру интерфейса: левая часть - холст canvas,
        правая часть - панель управления и информации
        """
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Левая панель: графический холст
        canvas_frame = ttk.Frame(main_container)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg="#18181b",
            highlightthickness=1,
            highlightbackground="#3f3f46"
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<Button-1>", lambda e: self.root.focus_set())

        # Правая панель: Управление и информация
        right_container = ttk.Frame(main_container, width=385)
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 5), pady=5)
        right_container.pack_propagate(False)

        v_scrollbar = ttk.Scrollbar(right_container, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.right_canvas = tk.Canvas(
            right_container,
            highlightthickness=0,
            yscrollcommand=v_scrollbar.set,
            bg=self.root.cget("bg")
        )
        self.right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.config(command=self.right_canvas.yview)

        self.scrollable_frame = ttk.Frame(self.right_canvas)
        self.canvas_window_id = self.right_canvas.create_window(
            (0, 0),
            window=self.scrollable_frame,
            anchor="nw"
        )

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.right_canvas.configure(scrollregion=self.right_canvas.bbox("all"))
        )
        self.right_canvas.bind(
            "<Configure>",
            lambda e: self.right_canvas.itemconfig(self.canvas_window_id, width=e.width)
        )

        def _on_mousewheel(event):
            self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        self.right_canvas.bind("<Enter>", lambda e: self.right_canvas.bind_all("<MouseWheel>", _on_mousewheel))
        self.right_canvas.bind("<Leave>", lambda e: self.right_canvas.unbind_all("<MouseWheel>"))

        # Блок: Режим удаления невидимых рёбер
        vis_group = ttk.LabelFrame(self.scrollable_frame, text=" Удаление невидимых рёбер ", padding=8)
        vis_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        vis_modes = [
            ("Удалить невидимые рёбра", "hidden_removed"),
            ("Показать невидимые пунктиром", "hidden_dashed"),
            ("Проволочный каркас (все рёбра)", "wireframe"),
        ]

        for text, val in vis_modes:
            rb = ttk.Radiobutton(
                vis_group,
                text=text,
                value=val,
                variable=self.vis_mode_var,
                command=self.redraw
            )
            rb.pack(anchor=tk.W, pady=2)

        ttk.Separator(vis_group, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(6, 4))
        self.cb_normals = ttk.Checkbutton(
            vis_group,
            text="Показать нормали граней N (N)",
            variable=self.normals_var,
            command=self._on_normals_toggle
        )
        self.cb_normals.pack(anchor=tk.W, pady=2)

        # Блок: Пошаговая демонстрация и параметры алгоритма
        demo_group = ttk.LabelFrame(self.scrollable_frame, text=" Демонстрация алгоритма (N · S > 0) ", padding=8)
        demo_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        step_btn_frame = ttk.Frame(demo_group)
        step_btn_frame.pack(fill=tk.X, pady=(0, 6))

        self.btn_step = ttk.Button(step_btn_frame,text="Пошагово: Грань (Tab)",command=self.next_algorithm_step)
        self.btn_step.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_step_reset = ttk.Button(step_btn_frame,text="Все грани",command=self.exit_step_mode,width=10)
        self.btn_step_reset.pack(side=tk.RIGHT)

        self.lbl_step_status = ttk.Label(demo_group,text="Режим: Расчёт всех 6 граней одновременно",
            font=("Arial", 8, "bold"),
            foreground="#0284c7"
        )
        self.lbl_step_status.pack(anchor=tk.W, pady=(0, 4))

        self.params_text = tk.Text(
            demo_group,
            height=8,
            font=("Consolas", 8),
            bg="#18181b",
            fg="#e4e4e7",
            relief=tk.FLAT,
            padx=6,
            pady=4,
            state=tk.DISABLED
        )
        self.params_text.pack(fill=tk.X)
        self.params_text.tag_configure("header", foreground="#94a3b8")
        self.params_text.tag_configure("vis", foreground="#4ade80")
        self.params_text.tag_configure("hid", foreground="#f87171")
        self.params_text.tag_configure("active", background="#1e3a8a", foreground="#ffffff")

        # Блок: Анимация (вращение)
        anim_group = ttk.LabelFrame(self.scrollable_frame, text=" Динамика (Вращение) ", padding=8)
        anim_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        self.btn_anim = ttk.Button(
            anim_group,
            text="Старт анимации (Пробел)",
            command=self.toggle_animation
        )
        self.btn_anim.pack(fill=tk.X, pady=(2, 6))

        lbl_rot = ttk.Label(anim_group, text="Ось вращения вокруг центра:", font=("Arial", 8, "bold"))
        lbl_rot.pack(anchor=tk.W, pady=(2, 2))

        rot_frame = ttk.Frame(anim_group)
        rot_frame.pack(fill=tk.X, pady=(0, 2))
        for ax in ("X", "Y", "Z", "XY"):
            rb = ttk.Radiobutton(
                rot_frame,
                text=f"Ось {ax}",
                value=ax,
                variable=self.anim_rot_axis_var
            )
            rb.pack(side=tk.LEFT, expand=True)

        # Блок выбора проекции
        proj_group = ttk.LabelFrame(self.scrollable_frame, text=" Проекция ", padding=8)
        proj_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        projections = [
            ("Изометрическая (3D)", "isometric"),
            ("Кабинетная (Косоугольная 45°)", "cabinet"),
            ("Перспективная (Камера c=30)", "perspective"),
            ("Вид спереди (Орто XY)", "ortho_xy"),
        ]

        for text, val in projections:
            rb = ttk.Radiobutton(
                proj_group,
                text=text,
                value=val,
                variable=self.projection_var,
                command=self.redraw
            )
            rb.pack(anchor=tk.W, pady=2)

        ttk.Separator(proj_group, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=(6, 4))
        self.cb_grid = ttk.Checkbutton(
            proj_group,
            text="Сетка плоскости XZ",
            variable=self.grid_var,
            command=self._on_grid_toggle
        )
        self.cb_grid.pack(anchor=tk.W, pady=2)

        # Блок информации о модели
        info_group = ttk.LabelFrame(self.scrollable_frame, text=" Информация о модели ", padding=8)
        info_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        v_count = len(self.model.vertices)
        e_count = len(self.model.edges)
        f_count = len(self.model.faces)
        cx, cy, cz = self.model.get_center()

        self.lbl_object = ttk.Label(
            info_group,
            text="Объект: Выпуклый 6-гранник (3, 4, 5 сторон)",
            font=("Arial", 9, "bold")
        )
        self.lbl_object.pack(anchor=tk.W, pady=1)

        self.lbl_stats = ttk.Label(info_group, text=f"Вершин: {v_count} | Рёбер: {e_count} | Граней: {f_count}")
        self.lbl_stats.pack(anchor=tk.W, pady=1)

        self.lbl_vis = ttk.Label(info_group, text="Видимых граней: - | Рёбер: -", foreground="#22c55e")
        self.lbl_vis.pack(anchor=tk.W, pady=1)

        self.lbl_center = ttk.Label(info_group, text=f"Центр C: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
        self.lbl_center.pack(anchor=tk.W, pady=1)

        self.lbl_action = ttk.Label(info_group, text=f"Действие: {self.last_action_text}", foreground="#0284c7")
        self.lbl_action.pack(anchor=tk.W, pady=1)

        # Блок: Горячие клавиши
        kbd_group = ttk.LabelFrame(self.scrollable_frame, text=" Управление (Клавиатура) ", padding=8)
        kbd_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        instructions = [
            ("Пробел", "Старт / Пауза вращения"),
            ("Tab", "Пошаговый обход граней F1..F6"),
            ("W / S", "Вращение вокруг центра X (±5°)"),
            ("A / D", "Вращение вокруг центра Y (±5°)"),
            ("Z / C", "Вращение вокруг центра Z (±5°)"),
            ("←  →", "Перемещение по оси X (±1.0)"),
            ("↑  ↓", "Перемещение по оси Y (±1.0)"),
            ("Q / E", "Перемещение по оси Z (±1.0)"),
            ("+ / -", "Масштаб модели (×1.1 / ×0.9)"),
            ("N", "Нормали граней N (Вкл / Выкл)"),
            ("G", "Сетка XZ (Вкл / Выкл)"),
            ("R", "Сброс всех трансформаций"),
        ]

        for keys, desc in instructions:
            row = ttk.Frame(kbd_group)
            row.pack(fill=tk.X, pady=1)
            lbl_k = ttk.Label(row, text=keys, font=("Consolas", 8, "bold"), width=9)
            lbl_k.pack(side=tk.LEFT)
            lbl_d = ttk.Label(row, text=desc, font=("Arial", 8))
            lbl_d.pack(side=tk.LEFT)

        btn_reset = ttk.Button(kbd_group, text="Сбросить всё к началу (R)", command=self.reset_model)
        btn_reset.pack(fill=tk.X, pady=(6, 2))

    def _on_key_press(self, event):
        """
        Обработчик клавиш клавиатуры
        Поддерживает английскую и русскую раскладки
        """
        keysym = event.keysym
        char = event.char.lower() if event.char else ""

        step_move = 1.0
        step_rot = math.radians(5.0)
        scale_up = 1.10
        scale_down = 1.0 / 1.10

        # Старт / Пауза анимации на пробел
        if keysym == "space" or char == " ":
            self.toggle_animation()
            return

        # Пошаговый обход граней на Tab
        if keysym == "Tab":
            self.next_algorithm_step()
            return "break"

        # Перемещение вдоль осей X, Y, Z
        if keysym == "Left":
            self.translate_model(-step_move, 0.0, 0.0, "Сдвиг: -X")
        elif keysym == "Right":
            self.translate_model(step_move, 0.0, 0.0, "Сдвиг: +X")
        elif keysym == "Up":
            self.translate_model(0.0, step_move, 0.0, "Сдвиг: +Y")
        elif keysym == "Down":
            self.translate_model(0.0, -step_move, 0.0, "Сдвиг: -Y")
        elif keysym == "Prior" or char in ("q", "й"):
            self.translate_model(0.0, 0.0, step_move, "Сдвиг: +Z (на нас)")
        elif keysym == "Next" or char in ("e", "у"):
            self.translate_model(0.0, 0.0, -step_move, "Сдвиг: -Z (вглубь)")

        # Вращение вокруг собственного геометрического центра
        elif char in ("w", "ц"):
            self.rotate_model_around_center(step_rot, 0.0, 0.0, "Вращение вокруг центра: +X (+5°)")
        elif char in ("s", "ы"):
            self.rotate_model_around_center(-step_rot, 0.0, 0.0, "Вращение вокруг центра: -X (-5°)")
        elif char in ("a", "ф"):
            self.rotate_model_around_center(0.0, -step_rot, 0.0, "Вращение вокруг центра: -Y (-5°)")
        elif char in ("d", "в"):
            self.rotate_model_around_center(0.0, step_rot, 0.0, "Вращение вокруг центра: +Y (+5°)")
        elif char in ("z", "я"):
            self.rotate_model_around_center(0.0, 0.0, step_rot, "Вращение вокруг центра: +Z (+5°)")
        elif char in ("c", "с"):
            self.rotate_model_around_center(0.0, 0.0, -step_rot, "Вращение вокруг центра: -Z (-5°)")

        # Равномерное масштабирование детали
        elif char in ("+", "=") or keysym in ("plus", "equal"):
            self.scale_model_around_center(scale_up, scale_up, scale_up, "Масштаб: ×1.1")
        elif char in ("-", "_") or keysym in ("minus", "underscore"):
            self.scale_model_around_center(scale_down, scale_down, scale_down, "Масштаб: ×0.9")

        # Переключение векторов нормалей граней
        elif char in ("n", "т"):
            self.show_normals = not self.show_normals
            self.normals_var.set(self.show_normals)
            self.last_action_text = f"Нормали граней: {'Вкл' if self.show_normals else 'Выкл'}"
            self.redraw()

        # Переключение координатной сетки
        elif char in ("g", "п"):
            self.show_grid = not self.show_grid
            self.grid_var.set(self.show_grid)
            self.last_action_text = f"Сетка XZ: {'Вкл' if self.show_grid else 'Выкл'}"
            self.redraw()

        # Сброс к исходному состоянию
        elif char in ("r", "к") or keysym in ("Home", "Escape"):
            self.reset_model()

    def _on_normals_toggle(self):
        """
        Переключает видимость векторов нормалей граней по клику на флажок в UI
        """
        self.show_normals = self.normals_var.get()
        self.last_action_text = f"Нормали граней: {'Вкл' if self.show_normals else 'Выкл'}"
        self.redraw()

    def _on_grid_toggle(self):
        """
        Переключает видимость координатной сетки XZ по клику на флажок в UI
        """
        self.show_grid = self.grid_var.get()
        self.last_action_text = f"Сетка XZ: {'Вкл' if self.show_grid else 'Выкл'}"
        self.redraw()

    def next_algorithm_step(self):
        """
        Шаг F1 -> F2 -> ... -> F6
        """
        total_faces = len(self.model.faces)
        if self.step_face_idx is None:
            self.step_face_idx = 0
        else:
            self.step_face_idx = (self.step_face_idx + 1) % total_faces

        self.last_action_text = f"Шаг алгоритма: проверка грани F{self.step_face_idx + 1}"
        self.redraw()

    def exit_step_mode(self):
        """
        Выходит из пошагового режима и отображает результат для всех граней сразу
        """
        self.step_face_idx = None
        self.last_action_text = "Режим: все грани одновременно"
        self.redraw()

    def toggle_animation(self):
        """
        Переключает состояние анимации: Старт / Пауза.
        """
        self.is_animating = not self.is_animating

        if self.is_animating:
            self.btn_anim.config(text="Пауза анимации (Пробел)")
            self.last_action_text = "Анимация: Запущена"
            self._animation_step()
        else:
            self.btn_anim.config(text="Старт анимации (Пробел)")
            self.last_action_text = "Анимация: Пауза"

        self.redraw()

    def _animation_step(self):
        """
        Один шаг анимации: вращение вокруг собственного геометрического центра C
        по выбранной оси
        """
        if not self.is_animating:
            return

        cx, cy, cz = self.model.get_center()
        rot_axis = self.anim_rot_axis_var.get()

        rx = self.anim_speed_rot if rot_axis in ("X", "XY") else 0.0
        ry = self.anim_speed_rot if rot_axis in ("Y", "XY") else 0.0
        rz = self.anim_speed_rot if rot_axis == "Z" else 0.0

        m_rot = rotation_around_center_matrix((cx, cy, cz), rx=rx, ry=ry, rz=rz)
        self.model.apply_matrix(m_rot)

        self.redraw()
        self.root.after(30, self._animation_step)

    def translate_model(self, dx, dy, dz, action_name):
        """
        Перемещает модель с помощью матрицы переноса T(dx, dy, dz)
        """
        m = translation_matrix(dx, dy, dz)
        self.model.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def rotate_model_around_center(self, rx, ry, rz, action_name):
        """
        Вращает модель вокруг её текущего геометрического центра C(xc, yc, zc):
        M = T(-C) * Rx * Ry * Rz * T(C)
        """
        center = self.model.get_center()
        m = rotation_around_center_matrix(center, rx=rx, ry=ry, rz=rz)
        self.model.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def scale_model_around_center(self, sx, sy, sz, action_name):
        """
        Масштабирует модель относительно её собственного геометрического центра:
        M = T(-C) * D(sx, sy, sz) * T(C)
        """
        cx, cy, cz = self.model.get_center()
        t_to_origin = translation_matrix(-cx, -cy, -cz)
        d_mat = scaling_matrix(sx, sy, sz)
        t_back = translation_matrix(cx, cy, cz)

        m = multiply_matrices(t_to_origin, d_mat, t_back)
        self.model.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def reset_model(self):
        """
        Сбрасывает положение, углы и масштаб модели в исходное состояние
        Если анимация была включена - ставит её на паузу
        """
        if self.is_animating:
            self.toggle_animation()

        self.step_face_idx = None
        self.model.reset()
        self.last_action_text = "Сброс к началу"
        self.redraw()

    def _get_current_projection_matrix(self):
        """
        Возвращает матрицу 4x4 для выбранной пользователем проекции.
        """
        proj_type = self.projection_var.get()
        match proj_type:
            case "isometric":
                return isometric_matrix()
            case "cabinet":
                return cabinet_matrix(angle_deg=45.0)
            case "perspective":
                return perspective_matrix(c=30.0)
            case "ortho_xy":
                return orthographic_xy_matrix()
            case _:
                return isometric_matrix()

    def redraw(self):
        """
        Полная перерисовка сцены на холсте
        """
        self.canvas.delete("all")

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w > 1:
            self.canvas_width = w
        if h > 1:
            self.canvas_height = h

        proj_matrix = self._get_current_projection_matrix()

        # Рисуем координатную сетку на плоскости XZ (Y = 0)
        if self.show_grid:
            self._draw_grid(proj_matrix)

        # Рисуем координатные оси
        self._draw_axes(proj_matrix)

        # Рисуем многогранник с удалением невидимых рёбер
        vis_info = self._draw_polyhedron(proj_matrix)

        # Рисуем геометрический центр модели
        self._draw_center(proj_matrix)

        # Обновляем таблицу параметров алгоритма
        self._update_algorithm_panel(vis_info)

        # Обновляем текстовые метки
        cx, cy, cz = self.model.get_center()
        vis_f = len(vis_info["visible_faces"])
        vis_e = len(vis_info["visible_edges"])
        self.lbl_vis.config(
            text=f"Видимых граней: {vis_f} из {len(self.model.faces)} | Рёбер: {vis_e} из {len(self.model.edges)}"
        )
        self.lbl_center.config(text=f"Центр C: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
        self.lbl_action.config(text=f"Действие: {self.last_action_text}")

    def _draw_grid(self, proj_matrix, grid_range=8, step=1):
        """
        Отрисовывает координатную сетку на плоскости XZ:
        """
        color_grid = "#262939"
        color_sub_axis = "#3b425b"

        # Линии, параллельные оси Z (при постоянном x)
        for x in range(-grid_range, grid_range + 1, step):
            col = color_sub_axis if x == 0 else color_grid
            p1 = project_point_to_screen(
                (float(x), 0.0, float(-grid_range)),
                proj_matrix,
                self.canvas_width,
                self.canvas_height,
                scale=self.scale,
                pan_x=self.pan_x,
                pan_y=self.pan_y
            )
            p2 = project_point_to_screen(
                (float(x), 0.0, float(grid_range)),
                proj_matrix,
                self.canvas_width,
                self.canvas_height,
                scale=self.scale,
                pan_x=self.pan_x,
                pan_y=self.pan_y
            )
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, width=1)

        # Линии, параллельные оси X (при постоянном z)
        for z in range(-grid_range, grid_range + 1, step):
            col = color_sub_axis if z == 0 else color_grid
            p1 = project_point_to_screen(
                (float(-grid_range), 0.0, float(z)),
                proj_matrix,
                self.canvas_width,
                self.canvas_height,
                scale=self.scale,
                pan_x=self.pan_x,
                pan_y=self.pan_y
            )
            p2 = project_point_to_screen(
                (float(grid_range), 0.0, float(z)),
                proj_matrix,
                self.canvas_width,
                self.canvas_height,
                scale=self.scale,
                pan_x=self.pan_x,
                pan_y=self.pan_y
            )
            self.canvas.create_line(p1[0], p1[1], p2[0], p2[1], fill=col, width=1)

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

    def _draw_polyhedron(self, proj_matrix):
        """
        Отрисовывает рёбра многогранника с учётом алгоритма удаления невидимых линий
        """
        pts = project_points_to_screen(
            self.model.vertices,
            proj_matrix,
            self.canvas_width,
            self.canvas_height,
            scale=self.scale,
            pan_x=self.pan_x,
            pan_y=self.pan_y
        )

        proj_type = self.projection_var.get()
        vis_info = classify_model_visibility(self.model, proj_type=proj_type, c=30.0)
        faces_data = vis_info["faces_data"]
        mode = self.vis_mode_var.get()

        # Если включён пошаговый режим — подсвечиваем текущую проверяемую грань
        if self.step_face_idx is not None:
            active_data = faces_data[self.step_face_idx]
            poly_coords = []
            for v_idx in active_data["face"]:
                poly_coords.extend(pts[v_idx])

            fill_col = "#14532d" if active_data["is_visible"] else "#450a0a"
            outline_col = "#4ade80" if active_data["is_visible"] else "#f87171"
            self.canvas.create_polygon(
                *poly_coords,
                fill=fill_col,
                outline=outline_col,
                width=2,
                stipple="gray50"
            )

        # В режиме полного каркаса рисуем все рёбра одинаково
        if mode == "wireframe":
            for i, j in self.model.edges:
                x1, y1 = pts[i]
                x2, y2 = pts[j]
                self.canvas.create_line(x1, y1, x2, y2, fill="#dbf838", width=2)

            # Точки на вершинах
            for px, py in pts:
                self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#f8fafc", outline="")
        else:
            # В пошаговом режиме собираем видимые рёбра только от уже проверенных граней
            if self.step_face_idx is not None:
                checked_vis_edges = set()
                for idx in range(self.step_face_idx + 1):
                    if faces_data[idx]["is_visible"]:
                        checked_vis_edges.update(faces_data[idx]["edges"])
                current_face_edges = set(faces_data[self.step_face_idx]["edges"])
            else:
                checked_vis_edges = {
                    (min(u, v), max(u, v)) for u, v in vis_info["visible_edges"]
                }
                current_face_edges = set()

            # Если включён показ невидимых рёбер пунктиром — рисуем их на заднем плане
            if mode == "hidden_dashed" or self.step_face_idx is not None:
                for i, j in self.model.edges:
                    edge_key = (min(i, j), max(i, j))
                    if edge_key not in checked_vis_edges:
                        x1, y1 = pts[i]
                        x2, y2 = pts[j]
                        self.canvas.create_line(x1, y1, x2, y2, fill="#64748b", width=1, dash=(4, 4))

            # Рисуем видимые рёбра сплошной яркой линией
            visible_vertex_indices = set()
            for i, j in self.model.edges:
                edge_key = (min(i, j), max(i, j))
                if edge_key in checked_vis_edges:
                    x1, y1 = pts[i]
                    x2, y2 = pts[j]
                    is_active_edge = (
                        self.step_face_idx is not None
                        and edge_key in current_face_edges
                        and faces_data[self.step_face_idx]["is_visible"]
                    )
                    color = "#38bdf8" if is_active_edge else "#dbf838"
                    width = 3 if is_active_edge else 2
                    self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)
                    visible_vertex_indices.add(i)
                    visible_vertex_indices.add(j)

            # Точки на вершинах (в режиме удаления рисуем только видимые вершины)
            vertex_pts = (
                pts
                if (mode == "hidden_dashed" or self.step_face_idx is not None)
                else [pts[idx] for idx in visible_vertex_indices]
            )
            for px, py in vertex_pts:
                self.canvas.create_oval(px - 2, py - 2, px + 2, py + 2, fill="#f8fafc", outline="")

        if self.show_normals or self.step_face_idx is not None:
            self._draw_face_normals(proj_matrix, faces_data)

        return vis_info

    def _draw_face_normals(self, proj_matrix, faces_data, normal_len=1.6):
        """
        Отрисовывает из центра каждой грани вектор внешней нормали N:
        зелёная сплошная стрелка — лицевая (видимая) грань,
        красная пунктирная стрелка — нелицевая (невидимая) грань
        """
        for fd in faces_data:
            idx = fd["index"]
            is_step_target = (self.step_face_idx == idx)

            if not self.show_normals and not is_step_target:
                continue

            fc = fd["center"]
            nx, ny, nz = fd["normal"]
            tip_3d = (
                fc[0] + nx * normal_len,
                fc[1] + ny * normal_len,
                fc[2] + nz * normal_len,
            )

            c_scr = project_point_to_screen(
                fc, proj_matrix, self.canvas_width, self.canvas_height,
                scale=self.scale, pan_x=self.pan_x, pan_y=self.pan_y
            )
            t_scr = project_point_to_screen(
                tip_3d, proj_matrix, self.canvas_width, self.canvas_height,
                scale=self.scale, pan_x=self.pan_x, pan_y=self.pan_y
            )

            col = "#22c55e" if fd["is_visible"] else "#ef4444"
            dash = () if fd["is_visible"] else (3, 3)
            w = 3 if is_step_target else 1.5

            self.canvas.create_oval(c_scr[0] - 2, c_scr[1] - 2, c_scr[0] + 2, c_scr[1] + 2, fill=col, outline="")
            self.canvas.create_line(
                c_scr[0], c_scr[1], t_scr[0], t_scr[1],
                fill=col, width=w, dash=dash, arrow=tk.LAST
            )
            self.canvas.create_text(
                t_scr[0] + 8, t_scr[1] - 6,
                text=f"F{idx + 1}",
                fill=col,
                font=("Consolas", 9, "bold")
            )

    def _update_algorithm_panel(self, vis_info):
        """
        Обновляет таблицу текущих параметров алгоритма (нормали N и скалярные произведения N*S)
        """
        faces_data = vis_info["faces_data"]

        if self.step_face_idx is None:
            self.lbl_step_status.config(
                text="Режим: Расчёт всех 6 граней одновременно",
                foreground="#0284c7"
            )
        else:
            fd = faces_data[self.step_face_idx]
            status_str = "ЛИЦЕВАЯ (ВИДИМА)" if fd["is_visible"] else "НЕЛИЦЕВАЯ (СКРЫТА)"
            self.lbl_step_status.config(
                text=f"Шаг {self.step_face_idx + 1}/6 — Грань F{self.step_face_idx + 1}: N·S = {fd['dot']:+.2f} -> {status_str}",
                foreground="#22c55e" if fd["is_visible"] else "#ef4444"
            )

        self.params_text.config(state=tk.NORMAL)
        self.params_text.delete("1.0", tk.END)

        self.params_text.insert(
            tk.END,
            " Грань Нормаль N            N·S   Статус\n",
            "header"
        )

        for fd in faces_data:
            idx = fd["index"]
            nx, ny, nz = fd["normal"]
            dot = fd["dot"]
            status = "ВИДИМА" if fd["is_visible"] else "СКРЫТА"
            prefix = "▶" if self.step_face_idx == idx else " "
            line = f"{prefix}F{idx + 1}({fd['sides']}) ({nx:+.2f},{ny:+.2f},{nz:+.2f}) {dot:+.2f}  {status}\n"

            if self.step_face_idx == idx:
                tag = "active"
            elif fd["is_visible"]:
                tag = "vis"
            else:
                tag = "hid"

            self.params_text.insert(tk.END, line, tag)

        self.params_text.config(state=tk.DISABLED)

    def _draw_center(self, proj_matrix):
        """
        Отрисовывает маркер геометрического центра модели
        """
        center = self.model.get_center()
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
