"""
Главный модуль - визуализирует 3D-проволочную букву «П», 
координатные оси и позволяет управлять аффинными преобразованиями,
включая динамическую трансформацию (анимацию)
"""

import math
import tkinter as tk
from tkinter import ttk

from model import create_letter_p, create_coordinate_axes
from transformations import (
    translation_matrix,
    scaling_matrix,
    rotation_around_center_matrix,
    reflection_xy_matrix,
    reflection_yz_matrix,
    reflection_zx_matrix,
    matrix_multiply,
    multiply_matrices
)
from projections import (
    orthographic_xy_matrix,
    orthographic_xz_matrix,
    orthographic_yz_matrix,
    cabinet_matrix,
    isometric_matrix,
    perspective_matrix,
    project_point_to_screen,
    project_points_to_screen
)


class GraphicsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Лабораторная работа №1: Аффинные преобразования и проецирование буквы «П» в 3D")
        self.root.geometry("1280x800")
        self.root.minsize(950, 650)

        # Модели буквы и осей
        self.letter = create_letter_p(width=6.0, height=8.0, thickness=1.5, depth=2.0)
        self.axes = create_coordinate_axes(length=9.0)

        # Параметры отображения
        self.scale = 28.0          # масштаб (пикселей на единицу модели)
        self.pan_x = 0.0           # смещение холста по горизонтали
        self.pan_y = 0.0           # смещение холста по вертикали
        self.canvas_width = 800
        self.canvas_height = 700

        # Текущая выбранная проекция
        self.projection_var = tk.StringVar(value="isometric")

        # Текст последнего действия
        self.last_action_text = "Готов к управлению"

        # Параметры анимации
        self.is_animating = False
        self.anim_rot_axis_var = tk.StringVar(value="Y")
        self.anim_trans_axis_var = tk.StringVar(value="Y")
        self.anim_speed_rot = math.radians(2.5)   # шаг угла вращения за кадр
        self.anim_step = 0.12                     # шаг перемещения вдоль выбранной оси
        self.anim_direction = 1.0                 # текущее направление движения
        self.anim_limit = 5.0                     # граница амплитуды перемещения

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
        right_container = ttk.Frame(main_container, width=355)
        right_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 5), pady=5)
        right_container.pack_propagate(False)

        # Добавил скроллбар потому что перестало помещаться в правую панель
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

        # Контейнер для всех виджетов внутри холста
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

        # Растягивание ширины содержимого под ширину панели
        self.right_canvas.bind(
            "<Configure>",
            lambda e: self.right_canvas.itemconfig(self.canvas_window_id, width=e.width)
        )

        # Прокрутка колесиком мыши при наведении курсора на правую панель
        def _on_mousewheel(event):
            self.right_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _bind_mousewheel(event):
            self.right_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            self.right_canvas.unbind_all("<MouseWheel>")

        self.right_canvas.bind("<Enter>", _bind_mousewheel)
        self.right_canvas.bind("<Leave>", _unbind_mousewheel)
        self.scrollable_frame.bind("<Enter>", _bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", _unbind_mousewheel)

        # Блок: Анимация
        anim_group = ttk.LabelFrame(self.scrollable_frame, text=" Динамическое преобразование ", padding=8)
        anim_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        self.btn_anim = ttk.Button(
            anim_group,
            text="Старт анимации (Пробел)",
            command=self.toggle_animation
        )
        self.btn_anim.pack(fill=tk.X, pady=(2, 6))

        # Выбор оси вращения вокруг центра
        lbl_rot = ttk.Label(anim_group, text="Вращение вокруг центра:", font=("Arial", 8, "bold"))
        lbl_rot.pack(anchor=tk.W, pady=(2, 1))

        rot_frame = ttk.Frame(anim_group)
        rot_frame.pack(fill=tk.X, pady=(0, 5))
        for ax in ("X", "Y", "Z"):
            rb = ttk.Radiobutton(
                rot_frame,
                text=f"Ось {ax}",
                value=ax,
                variable=self.anim_rot_axis_var
            )
            rb.pack(side=tk.LEFT, expand=True)

        # Выбор оси перемещения
        lbl_trans = ttk.Label(anim_group, text="Перемещение вдоль оси:", font=("Arial", 8, "bold"))
        lbl_trans.pack(anchor=tk.W, pady=(2, 1))

        trans_frame = ttk.Frame(anim_group)
        trans_frame.pack(fill=tk.X, pady=(0, 2))
        for ax in ("X", "Y", "Z"):
            rb = ttk.Radiobutton(
                trans_frame,
                text=f"Ось {ax}",
                value=ax,
                variable=self.anim_trans_axis_var
            )
            rb.pack(side=tk.LEFT, expand=True)

        # Блок выбора проекции
        proj_group = ttk.LabelFrame(self.scrollable_frame, text=" Проекция", padding=8)
        proj_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        projections = [
            ("Изометрическая (3D)", "isometric"),
            ("Кабинетная (Косоугольная 45°)", "cabinet"),
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
            rb.pack(anchor=tk.W, pady=2)

        # Блок информации о модели
        info_group = ttk.LabelFrame(self.scrollable_frame, text=" Информация о модели ", padding=8)
        info_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        v_count = len(self.letter.vertices)
        e_count = len(self.letter.edges)
        cx, cy, cz = self.letter.get_center()

        self.lbl_object = ttk.Label(info_group, text="Объект: 3D-буква «П»", font=("Arial", 9, "bold"))
        self.lbl_object.pack(anchor=tk.W, pady=1)

        self.lbl_stats = ttk.Label(info_group, text=f"Вершин: {v_count} | Рёбер: {e_count}")
        self.lbl_stats.pack(anchor=tk.W, pady=1)

        self.lbl_center = ttk.Label(info_group, text=f"Центр C: ({cx:.2f}, {cy:.2f}, {cz:.2f})")
        self.lbl_center.pack(anchor=tk.W, pady=1)

        self.lbl_action = ttk.Label(info_group, text=f"Действие: {self.last_action_text}", foreground="#0284c7")
        self.lbl_action.pack(anchor=tk.W, pady=1)

        # Блок: Горячие клавиши
        kbd_group = ttk.LabelFrame(self.scrollable_frame, text=" Управление (Клавиатура) ", padding=8)
        kbd_group.pack(fill=tk.X, pady=(0, 8), padx=2)

        instructions = [
            ("Пробел", "Старт / Пауза анимации"),
            ("←  →", "Перемещение по оси X (±1.0)"),
            ("↑  ↓", "Перемещение по оси Y (±1.0)"),
            ("Q / E", "Перемещение по оси Z (±1.0)"),
            ("W / S", "Вращение вокруг центра X (±5°)"),
            ("A / D", "Вращение вокруг центра Y (±5°)"),
            ("Z / C", "Вращение вокруг центра Z (±5°)"),
            ("+ / -", "Масштаб детали (×1.1 / ×0.9)"),
            ("1 / 2", "Растяжение по X (1.1 / 0.9)"),
            ("3 / 4", "Растяжение по Y (1.1 / 0.9)"),
            ("5 / 6", "Растяжение по Z (1.1 / 0.9)"),
            ("M", "Отражение по Y (вверх ногами)"),
            ("N", "Отражение по X (зеркало)"),
            ("B", "Отражение по Z"),
            ("R", "Сброс всех трансформаций"),
        ]

        for keys, desc in instructions:
            row = ttk.Frame(kbd_group)
            row.pack(fill=tk.X, pady=1)
            lbl_k = ttk.Label(row, text=keys, font=("Consolas", 8, "bold"), width=9)
            lbl_k.pack(side=tk.LEFT)
            lbl_d = ttk.Label(row, text=desc, font=("Arial", 8))
            lbl_d.pack(side=tk.LEFT)

        # Кнопка сброса
        btn_reset = ttk.Button(kbd_group, text="Сбросить всё к началу (R)", command=self.reset_model)
        btn_reset.pack(fill=tk.X, pady=(6, 2))

        # Легенда координатных осей
        legend_frame = ttk.LabelFrame(self.scrollable_frame, text=" Оси координат ", padding=8)
        legend_frame.pack(fill=tk.X, pady=(0, 5), padx=2)

        lbl_x = tk.Label(legend_frame, text="Ось X — Красная", fg="#ef4444")
        lbl_x.pack(anchor=tk.W)
        lbl_y = tk.Label(legend_frame, text="Ось Y — Зеленая", fg="#22c55e")
        lbl_y.pack(anchor=tk.W)
        lbl_z = tk.Label(legend_frame, text="Ось Z — Синяя", fg="#38bdf8")
        lbl_z.pack(anchor=tk.W)

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

        # Масштабирование по отдельным осям
        elif char == "1":
            self.scale_model_around_center(scale_up, 1.0, 1.0, "Растяжение по X (1.1)")
        elif char == "2":
            self.scale_model_around_center(scale_down, 1.0, 1.0, "Сжатие по X (0.9)")
        elif char == "3":
            self.scale_model_around_center(1.0, scale_up, 1.0, "Растяжение по Y (1.1)")
        elif char == "4":
            self.scale_model_around_center(1.0, scale_down, 1.0, "Сжатие по Y (0.9)")
        elif char == "5":
            self.scale_model_around_center(1.0, 1.0, scale_up, "Растяжение по Z (1.1)")
        elif char == "6":
            self.scale_model_around_center(1.0, 1.0, scale_down, "Сжатие по Z (0.9)")

        # Отражение относительно собственного центра
        elif char in ("m", "ь"):
            self.reflect_model_around_center("y", "Отражение по Y (вверх ногами)")
        elif char in ("n", "т"):
            self.reflect_model_around_center("x", "Отражение по X (зеркало)")
        elif char in ("b", "и"):
            self.reflect_model_around_center("z", "Отражение по Z")

        # Сброс к исходному состоянию
        elif char in ("r", "к") or keysym in ("Home", "Escape"):
            self.reset_model()

    def toggle_animation(self):
        """
        Переключает состояние анимации: Старт / Пауза.
        """
        self.is_animating = not self.is_animating

        if self.is_animating:
            self.btn_anim.config(text="Пауза анимации (Пробел)")
            self.last_action_text = "Анимация: Запущена"
            # Запускаем цикл анимации
            self._animation_step()
        else:
            self.btn_anim.config(text="Старт анимации (Пробел)")
            self.last_action_text = "Анимация: Пауза"

        self.redraw()

    def _animation_step(self):
        """
        Один шаг анимации:
        1. Вращение вокруг собственного геометрического центра C по выбранной оси
        2. Одновременное гармоническое перемещение вдоль выбранной оси
        3. Матрица шага: M_step = M_rot_center * M_translation.
        """
        if not self.is_animating:
            return

        cx, cy, cz = self.letter.get_center()

        # Вращение вокруг собственного геометрического центра по выбранной оси
        rot_axis = self.anim_rot_axis_var.get()
        rx = self.anim_speed_rot if rot_axis == "X" else 0.0
        ry = self.anim_speed_rot if rot_axis == "Y" else 0.0
        rz = self.anim_speed_rot if rot_axis == "Z" else 0.0

        m_rot = rotation_around_center_matrix((cx, cy, cz), rx=rx, ry=ry, rz=rz)

        # Перемещение вдоль выбранной оси с разворотом у границ
        trans_axis = self.anim_trans_axis_var.get()
        if trans_axis == "X":
            curr_coord = cx
        elif trans_axis == "Y":
            curr_coord = cy
        else:
            curr_coord = cz

        if curr_coord >= self.anim_limit:
            self.anim_direction = -1.0
        elif curr_coord <= -self.anim_limit:
            self.anim_direction = 1.0

        step = self.anim_step * self.anim_direction
        dx = step if trans_axis == "X" else 0.0
        dy = step if trans_axis == "Y" else 0.0
        dz = step if trans_axis == "Z" else 0.0

        m_trans = translation_matrix(dx, dy, dz)

        # Составная матрица шага анимации: вращение + перемещение
        m_step = matrix_multiply(m_rot, m_trans)

        # Применяем матрицу к модели буквы
        self.letter.apply_matrix(m_step)

        # Перерисовываем холст
        self.redraw()

        # Планируем следующий кадр через 30 миллисекунд
        self.root.after(30, self._animation_step)

    def translate_model(self, dx, dy, dz, action_name):
        """
        Перемещает букву с помощью матрицы переноса T(dx, dy, dz)
        """
        m = translation_matrix(dx, dy, dz)
        self.letter.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def rotate_model_around_center(self, rx, ry, rz, action_name):
        """
        Вращает букву вокруг её текущего геометрического центра C(xc, yc, zc):
        M = T(-C) * Rx * Ry * Rz * T(C)
        """
        center = self.letter.get_center()
        m = rotation_around_center_matrix(center, rx=rx, ry=ry, rz=rz)
        self.letter.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def scale_model_around_center(self, sx, sy, sz, action_name):
        """
        Масштабирует букву относительно её собственного геометрического центра:
        M = T(-C) * D(sx, sy, sz) * T(C)
        """
        cx, cy, cz = self.letter.get_center()
        t_to_origin = translation_matrix(-cx, -cy, -cz)
        d_mat = scaling_matrix(sx, sy, sz)
        t_back = translation_matrix(cx, cy, cz)

        m = multiply_matrices(t_to_origin, d_mat, t_back)
        self.letter.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def reflect_model_around_center(self, axis, action_name):
        """
        Отражает 3D-букву относительно её собственного центра:
        M = T(-C) * M_reflection * T(C)
        """
        cx, cy, cz = self.letter.get_center()
        t_to_origin = translation_matrix(-cx, -cy, -cz)
        if axis == "x":
            m_ref = reflection_yz_matrix()
        elif axis == "y":
            m_ref = reflection_zx_matrix()
        else:
            m_ref = reflection_xy_matrix()
        t_back = translation_matrix(cx, cy, cz)

        m = multiply_matrices(t_to_origin, m_ref, t_back)
        self.letter.apply_matrix(m)
        self.last_action_text = action_name
        self.redraw()

    def reset_model(self):
        """
        Сбрасывает положение, углы и масштаб буквы в исходное состояние
        Если анимация была включена - ставит её на паузу
        """
        if self.is_animating:
            self.toggle_animation()

        self.letter.reset()
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
        self.lbl_action.config(text=f"Действие: {self.last_action_text}")

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
