import pygame
import sys
import math

pygame.init()

pygame.display.set_caption("point and line ")
#素材及杂项
map_width = 800
map_height = 600

gamescreen = pygame.display.set_mode((map_width, map_height), pygame.RESIZABLE)

color = (255, 240, 245)

point_img = pygame.image.load("image/point.png")
circle_img = pygame.image.load("image/circles.png")
Icon = pygame.image.load("image/icon.png")
pygame.display.set_icon(Icon)
clock = pygame.time.Clock()
target_fps = 60

# 字体设置
font_path = "chineseblack.ttf" 
font_size = 24 
font = pygame.font.Font(font_path, font_size)


#游戏参数
list_point = []
list_circles = []
player = 1  #默认方块先手（当然你可以在这里修改先后手）
#游戏回合
game_round=0
# 碰撞箱半径
COLLISION_RADIUS = 10
# 存储各类型点的线段
segments_point = []  
segments_circle = []  

# 存储断线的标记
broken_segments_point = []  
broken_segments_circle = [] 

# 存储面
enclosed_areas_point = []  
enclosed_areas_circle = []  

# 提示信息（）
message = ""
message_timer = 0


# 连线预览
preview_line = None
preview_line_type = None

# 缩放相关变量
zoom_level = 1.0
min_zoom = 0.5
max_zoom = 3.0
offset_x = 0
offset_y = 0
dragging = False
last_mouse_pos = (0, 0)

running = True
#计算两线是否相交
def world_to_screen(x, y):
    """将世界坐标转换为屏幕坐标"""
    screen_x = (x - offset_x) * zoom_level + map_width / 2
    screen_y = (y - offset_y) * zoom_level + map_height / 2
    return screen_x, screen_y

def screen_to_world(x, y):
    """将屏幕坐标转换为世界坐标"""
    world_x = (x - map_width / 2) / zoom_level + offset_x
    world_y = (y - map_height / 2) / zoom_level + offset_y
    return world_x, world_y

def line_intersection(line1, line2):
    """检查两条线段是否相交，如果相交返回交点，否则返回None"""
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2
    
    # 计算分母
    denom = (y4 - y3) * (x2 - x1) - (x4 - x3) * (y2 - y1)
    
    # 如果分母为0，说明线段平行
    if denom == 0:
        return None
    
    ua = ((x4 - x3) * (y1 - y3) - (y4 - y3) * (x1 - x3)) / denom
    ub = ((x2 - x1) * (y1 - y3) - (y2 - y1) * (x1 - x3)) / denom
    
    # 如果ua和ub都在0和1之间，说明线段相交
    if 0 <= ua <= 1 and 0 <= ub <= 1:
        x = x1 + ua * (x2 - x1)
        y = y1 + ua * (y2 - y1)
        return (x, y)
    
    return None
#碰撞体积控制逻辑
def check_line_collision(line_start, line_end, points_to_check, exclude_points=[]):
    """检查线段是否与任何点的碰撞箱相交"""
    for point in points_to_check:
        # 跳过起点和终点
        if point in exclude_points:
            continue
            
        # 计算点到线段的距离
        distance = point_to_line_distance(point, line_start, line_end)
        
        # 如果距离小于碰撞半径，则发生碰撞
        if distance < COLLISION_RADIUS:
            return True
            
    return False

def check_point_collision(new_point, existing_points, min_distance=None):
    """检查新点是否与任何已有点太近"""
    if min_distance is None:
        min_distance = COLLISION_RADIUS * 1  #碰撞半径为最小距离
    
    for point in existing_points:
        # 计算两点之间的距离
        distance = math.sqrt((point[0] - new_point[0])**2 + (point[1] - new_point[1])**2)
        
        # 如果距离小于最小距离，则发生碰撞
        if distance < min_distance:
            return True
            
    return False


#这里是判断面内是否有点的监测方法：
#is_point_inside_polygon：纯粹的几何算法，负责单个多边形检测
#is_point_in_enclosed_areas：游戏逻辑，负责遍历所有封闭区域
#它们是互补的关系
def is_point_inside_polygon(point, polygon):
    """判断点是否在多边形内部 - 使用射线法"""
    x, y = point
    n = len(polygon)
    inside = False
    
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    
    return inside

def is_point_in_enclosed_areas(point, enclosed_areas):
    """检查点是否在任何封闭区域内"""
    for area in enclosed_areas:
        if is_point_inside_polygon(point, area):
            return True
    return False

def is_line_in_enclosed_areas(line_start, line_end, enclosed_areas):
    """检查线段是否在任何封闭区域内（两个端点都在区域内）"""
    for area in enclosed_areas:
        if is_point_inside_polygon(line_start, area) and is_point_inside_polygon(line_end, area):
            return True
    return False

def find_cycles(segments):
    """从线段中找出所有封闭多边形 - 改进版本"""
    if len(segments) < 3:
        return []
    
    # 构建邻接表
    graph = {}
    for seg in segments:
        p1, p2 = seg
        if p1 not in graph:
            graph[p1] = []
        if p2 not in graph:
            graph[p2] = []
        graph[p1].append(p2)
        graph[p2].append(p1)
    
    cycles = []
    visited_edges = set()
    
    for start_point in graph:
        stack = [(start_point, [start_point])]
        
        while stack:
            current, path = stack.pop()
            
            # 如果路径长度超过20，停止搜索（防止无限循环）
            if len(path) > 20:
                continue
                
            for neighbor in graph.get(current, []):
                # 检查是否形成环
                if neighbor == start_point and len(path) >= 3:
                    # 找到环，添加到结果中
                    cycle = path[:]
                    # 检查这个环是否已经存在（不同顺序）
                    is_duplicate = False
                    for existing in cycles:
                        if set(existing) == set(cycle):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        cycles.append(cycle)
                    continue
                
                # 避免重复访问边
                edge = tuple(sorted([current, neighbor]))
                if edge not in visited_edges and neighbor not in path:
                    visited_edges.add(edge)
                    stack.append((neighbor, path + [neighbor]))
                    visited_edges.remove(edge)  # 回溯
    
    return cycles




def check_enclosed_points_and_segments():
    """检查是否有封闭区域，并移除被围住的点和线段 - 改进版本"""
    global list_point, list_circles, segments_point, segments_circle
    global broken_segments_point, broken_segments_circle
    global enclosed_areas_point, enclosed_areas_circle
    
    # 获取所有有效的线段（未被断开的）
    valid_point_segments = [seg for i, seg in enumerate(segments_point) if i not in broken_segments_point]
    valid_circle_segments = [seg for i, seg in enumerate(segments_circle) if i not in broken_segments_circle]
    
    # 找出所有方块线段形成的封闭多边形
    point_cycles = find_cycles(valid_point_segments)
    
    # 找出所有圆圈线段形成的封闭多边形
    circle_cycles = find_cycles(valid_circle_segments)
    
    # 更新封闭区域
    enclosed_areas_point = point_cycles
    enclosed_areas_circle = circle_cycles
    
    removed_anything = False
    
    # 检查每个方块多边形，移除内部的圆圈点和圆圈线段
    for cycle in point_cycles:
        # 移除内部的圆圈点
        points_to_remove = []
        for i, point in enumerate(list_circles):
            if is_point_inside_polygon(point, cycle):
                points_to_remove.append(i)
        
        # 从后往前删除，避免索引问题
        for i in sorted(points_to_remove, reverse=True):
            del list_circles[i]
            removed_anything = True
        
        # 移除内部的圆圈线段（如果两个端点都在内部）
        segments_to_remove = []
        for i, seg in enumerate(segments_circle):
            if i not in broken_segments_circle:
                p1, p2 = seg
                if is_point_inside_polygon(p1, cycle) and is_point_inside_polygon(p2, cycle):
                    segments_to_remove.append(i)
        
        # 标记这些线段为断开
        broken_segments_circle.extend(segments_to_remove)
        
        if len(segments_to_remove) > 0:
            print(f"方块多边形围住了 {len(segments_to_remove)} 条圆圈线段")
            removed_anything = True
    
    # 检查每个圆圈多边形，移除内部的方块点和方块线段
    for cycle in circle_cycles:
        # 移除内部的方块点
        points_to_remove = []
        for i, point in enumerate(list_point):
            if is_point_inside_polygon(point, cycle):
                points_to_remove.append(i)
        
        # 从后往前删除，避免索引问题
        for i in sorted(points_to_remove, reverse=True):
            del list_point[i]
            removed_anything = True
        
        # 移除内部的方块线段（如果两个端点都在内部）
        segments_to_remove = []
        for i, seg in enumerate(segments_point):
            if i not in broken_segments_point:
                p1, p2 = seg
                if is_point_inside_polygon(p1, cycle) and is_point_inside_polygon(p2, cycle):
                    segments_to_remove.append(i)
        
        # 标记这些线段为断开
        broken_segments_point.extend(segments_to_remove)
        
        if len(segments_to_remove) > 0:
            print(f"圆圈多边形围住了 {len(segments_to_remove)} 条方块线段")
            removed_anything = True

def check_and_break_segments(new_segment, segment_type):
    """检查新线段是否与另一类型的线段相交，如果相交则只断开另一类型的线"""
    global segments_point, segments_circle, broken_segments_point, broken_segments_circle
    
    broken_any = False
    
    if segment_type == "point":
        # 新的是方块线段，检查所有圆圈线段
        for i, circle_seg in enumerate(segments_circle):
            # 如果这个圆圈线段已经被断开，跳过检查
            if i in broken_segments_circle:
                continue
                
            intersection = line_intersection(new_segment, circle_seg)
            if intersection:
                # 找到交点，只断开另一类型的线（圆圈线段）
                print(f"方块线段与圆圈线段相交于 {intersection}，断掉圆圈线段")
                # 只将相交的圆圈线段标记为断开，新线段不断
                broken_segments_circle.append(i)
                broken_any = True
    else:  # segment_type == "circle"
        # 新的是圆圈线段，检查所有方块线段
        for i, point_seg in enumerate(segments_point):
            # 如果这个方块线段已经被断开，跳过检查
            if i in broken_segments_point:
                continue
                
            intersection = line_intersection(new_segment, point_seg)
            if intersection:
                # 找到交点，只断开另一类型的线（方块线段）
                print(f"圆圈线段与方块线段相交于 {intersection}，断掉方块线段")
                # 只将相交的方块线段标记为断开，新线段不断
                broken_segments_point.append(i)
                broken_any = True
    
    return broken_any





#连线的预览
def draw_dashed_line(surface, color, start_pos, end_pos, dash_length=10):
    # 计算线段的方向和长度
    dx = end_pos[0] - start_pos[0]
    dy = end_pos[1] - start_pos[1]
    line_length = ((dx)**2 + (dy)**2)**0.5
    
    # 计算单位向量
    if line_length > 0:
        dx /= line_length
        dy /= line_length
    
    # 绘制虚线
    drawn_length = 0
    while drawn_length < line_length:
        # 计算当前段的结束位置
        segment_end = min(line_length, drawn_length + dash_length)
        
        # 计算起点和终点坐标
        start_x = start_pos[0] + dx * drawn_length
        start_y = start_pos[1] + dy * drawn_length
        end_x = start_pos[0] + dx * segment_end
        end_y = start_pos[1] + dy * segment_end
        
        # 绘制线段段
        pygame.draw.line(surface, color, (start_x, start_y), (end_x, end_y), 2)
        
        # 更新已绘制长度
        drawn_length = segment_end + dash_length

#文字显示
def show_message(msg):
    global message, message_timer
    message = msg
    message_timer = 120  # 显示2秒（60帧/秒）
    print(msg)
#切换玩家
def switch_player():
    global player,game_round
    player = 2 if player == 1 else 1
    game_round +=1
#缩放
def point_to_line_distance(point, line_start, line_end):
    #计算点到线段的距离
    x, y = point
    x1, y1 = line_start
    x2, y2 = line_end
    
    l2 = (x2 - x1)**2 + (y2 - y1)**2
    
    #如果线段长度为0，返回点到点的距离
    if l2 == 0:
        return math.sqrt((x - x1)**2 + (y - y1)**2)
    
    #计算投影参数t
    t = max(0, min(1, ((x - x1) * (x2 - x1) + (y - y1) * (y2 - y1)) / l2))
    
    #计算投影点
    projection_x = x1 + t * (x2 - x1)
    projection_y = y1 + t * (y2 - y1)
    
    #返回点到投影点的距离
    return math.sqrt((x - projection_x)**2 + (y - projection_y)**2)
#win
def pygame_player():
    global player,game_round
    player=2 if player ==1 else 1
    game_round+=1

#主要游戏逻辑，包括连线，断线，吞噬
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.VIDEORESIZE:
            map_width, map_height = event.size
            gamescreen = pygame.display.set_mode((map_width, map_height), pygame.RESIZABLE)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  #左键放置点
                #将屏幕坐标转换为世界坐标
                screen_pos = pygame.mouse.get_pos()
                pos = screen_to_world(screen_pos[0], screen_pos[1])
                
                #是否两点距离过近
                all_points = list_point + list_circles
                if check_point_collision(pos, all_points):
                    show_message("我草泥马阳西一中")
                    continue
                
                # 检查是否在对方面内
                if player == 1:  #方块玩家
                    if is_point_in_enclosed_areas(pos, enclosed_areas_circle):
                        show_message("不能在对方面内落点")
                        continue
                else:  #圆圈玩家
                    if is_point_in_enclosed_areas(pos, enclosed_areas_point):
                        show_message("不能在对方面内落点")
                        continue
                
                if player == 1:
                    list_point.append(pos)
                    switch_player()  #切换玩家
                else:
                    list_circles.append(pos)
                    switch_player()  #切换玩家
                    
            elif event.button == 3:  #右键连线
                #将屏幕坐标转换为世界坐标
                screen_pos = pygame.mouse.get_pos()
                pos = screen_to_world(screen_pos[0], screen_pos[1])
                
                #检查是否点击了点
                clicked_point = None
                clicked_type = None
                
                #根据当前玩家检查对应类型的点
                if player == 1:
                    #玩家1只能连接方块点
                    for point in list_point:
                        distance = math.sqrt((point[0] - pos[0])**2 + (point[1] - pos[1])**2)
                        if distance < COLLISION_RADIUS:
                            clicked_point = point
                            clicked_type = "point"
                            break
                else:
                    #玩家2只能连接圆圈点
                    for point in list_circles:
                        distance = math.sqrt((point[0] - pos[0])**2 + (point[1] - pos[1])**2)
                        if distance < COLLISION_RADIUS:
                            clicked_point = point
                            clicked_type = "circle"
                            break
                
                #设置预览线
                if clicked_point is not None:
                    preview_line = (clicked_point, pos)
                    preview_line_type = clicked_type
            
            elif event.button == 2:  #中键按下，开始拖动（ai写的这里我理解不了什么意思）
                dragging = True
                last_mouse_pos = pygame.mouse.get_pos()

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 3 and preview_line is not None:  # 右键释放，尝试连线
                start_point = preview_line[0]
                screen_end_pos = pygame.mouse.get_pos()
                end_pos = screen_to_world(screen_end_pos[0], screen_end_pos[1])
                
                # 检查是否释放到了点上
                end_point = None
                end_type = None


                # 根据当前玩家检查对应类型的点
                if player == 1:
                    # 玩家1只能连接方块点
                    for point in list_point:
                        distance = math.sqrt((point[0] - end_pos[0])**2 + (point[1] - end_pos[1])**2)
                        if distance < COLLISION_RADIUS:
                            end_point = point
                            end_type = "point"
                            break
                else:
                    # 玩家2只能连接圆圈点
                    for point in list_circles:
                        distance = math.sqrt((point[0] - end_pos[0])**2 + (point[1] - end_pos[1])**2)
                        if distance < COLLISION_RADIUS:
                            end_point = point
                            end_type = "circle"
                            break
                
                # 连线逻辑
                if end_point is not None and end_type == preview_line_type and start_point != end_point:
                    # 检查线段是否经过其他点的碰撞箱
                    all_points = list_point + list_circles
                    exclude_points = [start_point, end_point]
                    
                    if check_line_collision(start_point, end_point, all_points, exclude_points):
                        show_message("你不能连接这两个点")
                        #监测面内点逻辑
                    else:
                        if player == 1: 
                            if is_line_in_enclosed_areas(start_point, end_point, enclosed_areas_circle):
                                show_message("不能在对方面内连线")
                            else:
                                new_segment = (start_point, end_point)
                                segments_point.append(new_segment)
                                check_and_break_segments(new_segment, "point")
                                check_enclosed_points_and_segments()
                                switch_player()
                        else:  
                            if is_line_in_enclosed_areas(start_point, end_point, enclosed_areas_point):
                                show_message("不能在对方面内连线")
                            else:
                                new_segment = (start_point, end_point)
                                segments_circle.append(new_segment)
                                check_and_break_segments(new_segment, "circle")                              
                                check_enclosed_points_and_segments()
                                switch_player()
                
                # 重置预览线
                preview_line = None
                preview_line_type = None
            
            elif event.button == 2:  # 中键释放，停止拖动
                dragging = False

        elif event.type == pygame.MOUSEMOTION:
            # 更新预览线的终点
            if preview_line is not None:
                screen_pos = pygame.mouse.get_pos()
                world_pos = screen_to_world(screen_pos[0], screen_pos[1])
                preview_line = (preview_line[0], world_pos)
            
            #连线拖动
            if dragging:
                current_mouse_pos = pygame.mouse.get_pos()
                dx = current_mouse_pos[0] - last_mouse_pos[0]
                dy = current_mouse_pos[1] - last_mouse_pos[1]
                
                # 更新偏移量
                offset_x -= dx / zoom_level
                offset_y -= dy / zoom_level
                
                last_mouse_pos = current_mouse_pos

        elif event.type == pygame.MOUSEWHEEL:


# 滚轮缩放
            old_zoom = zoom_level
            
            # 调整缩放级别
            if event.y > 0:
                zoom_level = min(zoom_level * 1.1, max_zoom)
            elif event.y < 0:
                zoom_level = max(zoom_level / 1.1, min_zoom)
            
            #屏幕坐标位置（鼠标位置）
            mouse_x, mouse_y = pygame.mouse.get_pos()
            #世界坐标位置
            world_x, world_y = screen_to_world(mouse_x, mouse_y)
            
            # 调整偏移量，缩放以鼠标位置为中心
            offset_x = world_x - (mouse_x - map_width / 2) / zoom_level
            offset_y = world_y - (mouse_y - map_height / 2) / zoom_level

#退出
    keys = pygame.key.get_pressed()
    if keys[pygame.K_ESCAPE]:
        running = False
#别点我啊混蛋CtrlLLLLLLLLLLLLLLLLL
    elif keys[pygame.K_LCTRL]:
        running=False
    gamescreen.fill(color)

#线
    # 绘制方块点之间的线段（只绘制未断开的线段）
    for i, segment in enumerate(segments_point):
        if i not in broken_segments_point:
            start_screen = world_to_screen(segment[0][0], segment[0][1])
            end_screen = world_to_screen(segment[1][0], segment[1][1])
            pygame.draw.line(gamescreen, (255,182,193), start_screen, end_screen, 2)
    
    # 绘制圆圈点之间的线段（只绘制未断开的线段）
    for i, segment in enumerate(segments_circle):
        if i not in broken_segments_circle:
            start_screen = world_to_screen(segment[0][0], segment[0][1])
            end_screen = world_to_screen(segment[1][0], segment[1][1])
            pygame.draw.line(gamescreen, (64,224,208), start_screen, end_screen, 2)
    
    # 绘制预览线
    if preview_line is not None:
        start_screen = world_to_screen(preview_line[0][0], preview_line[0][1])
        end_screen = world_to_screen(preview_line[1][0], preview_line[1][1])
        
        # 检查预览线是否有效
        start_point = preview_line[0]
        end_pos = preview_line[1]
        
        # 检查是否悬停在点上
        hover_point = None
        hover_type = None
        
        # 根据当前玩家检查对应类型的点
        if player == 1:
            # 玩家1只能连接方块点
            for point in list_point:
                distance = math.sqrt((point[0] - end_pos[0])**2 + (point[1] - end_pos[1])**2)
                if distance < COLLISION_RADIUS:
                    hover_point = point
                    hover_type = "point"
                    break
        else:
            # 玩家2只能连接圆圈点
            for point in list_circles:
                distance = math.sqrt((point[0] - end_pos[0])**2 + (point[1] - end_pos[1])**2)
                if distance < COLLISION_RADIUS:
                    hover_point = point
                    hover_type = "circle"
                    break
        
        # 如果悬停在了点上且类型相同，绘制虚线预览
        if hover_point is not None and hover_type == preview_line_type and start_point != hover_point:
            # 检查线段是否经过其他点的碰撞箱
            all_points = list_point + list_circles
            exclude_points = [start_point, hover_point]
            
            # 检查是否在对方封闭区域内
            in_enclosed_area = False
            if player == 1:  # 方块玩家
                in_enclosed_area = is_line_in_enclosed_areas(start_point, hover_point, enclosed_areas_circle)
            else:  # 圆圈玩家
                in_enclosed_area = is_line_in_enclosed_areas(start_point, hover_point, enclosed_areas_point)
            
            if check_line_collision(start_point, hover_point, all_points, exclude_points) or in_enclosed_area:
                # 如果碰撞或在封闭区域内，绘制红色虚线
                draw_dashed_line(gamescreen, (255, 0, 0), start_screen, world_to_screen(hover_point[0], hover_point[1]))
            else:
                # 如果无碰撞，绘制灰色虚线
                draw_dashed_line(gamescreen, (150, 150, 150), start_screen, world_to_screen(hover_point[0], hover_point[1]))
        else:
            # 如果悬停位置无效，绘制红色虚线
            draw_dashed_line(gamescreen, (255, 0, 0), start_screen, end_screen)
    
#点
    for pos in list_point:
        screen_x, screen_y = world_to_screen(pos[0], pos[1])
# 缩放图片大小
        scaled_width = point_img.get_width() * zoom_level
        scaled_height = point_img.get_height() * zoom_level
        scaled_point_img = pygame.transform.scale(point_img, (int(scaled_width), int(scaled_height)))
        x = screen_x - scaled_point_img.get_width() // 2
        y = screen_y - scaled_point_img.get_height() // 2
        gamescreen.blit(scaled_point_img, (x, y))
    
    for pos in list_circles:
        screen_x, screen_y = world_to_screen(pos[0], pos[1])
# 缩放图片大小
        scaled_width = circle_img.get_width() * zoom_level
        scaled_height = circle_img.get_height() * zoom_level
        scaled_circle_img = pygame.transform.scale(circle_img, (int(scaled_width), int(scaled_height)))
        x = screen_x - scaled_circle_img.get_width() // 2
        y = screen_y - scaled_circle_img.get_height() // 2
        gamescreen.blit(scaled_circle_img, (x, y))
    
    # 显示当前玩家信息
    player_text = f"Round: {'方块' if player == 1 else '圆圈'}"
    try:
        player_surface = font.render(player_text, True, (0, 0, 0))
        gamescreen.blit(player_surface, (10, 10))
    except Exception as e:
        print(f"字体渲染错误: {e}")
    
    # 显示缩放级别
    zoom_text = f"Zoom: {zoom_level:.1f}x"
    try:
        zoom_surface = font.render(zoom_text, True, (0, 0, 0))
        gamescreen.blit(zoom_surface, (10, 50))
    except Exception as e:
        print(f"字体渲染错误: {e}")
    round_text = f"回合: {game_round}"
    try:
        round_surface = font.render(round_text, True, (0, 0, 0))  # 黑色
        gamescreen.blit(round_surface, (10, 90))
    except Exception as e:
        print(f"字体渲染错误: {e}")
    # 显示消息
    if message_timer > 0:
        try:
            message_surface = font.render(message, True, (0, 0,123 ))
            gamescreen.blit(message_surface, (map_width // 2 - message_surface.get_width() // 2, 20))
        except Exception as e:
            print(f"字体渲染错误: {e}")
        message_timer -= 1
#win chexk
    point_count = len(list_point)
    circle_count = len(list_circles)

    if game_round>20:
        if game_round > 0 and game_round > 0 and game_round != circle_count:
            winner = "方块" if point_count > circle_count else "圆圈"
            win_text = f"{winner}玩家获胜!"
            try:
                win_font = pygame.font.SysFont('simhei', 36) if 'simhei' in pygame.font.get_fonts() else pygame.font.Font(None, 72)
                win_surface = win_font.render(win_text, True, (0, 0, 0)) 
                win_rect = win_surface.get_rect(center=(map_width // 2, map_height // 2))
            
                s = pygame.Surface((map_width, map_height), pygame.SRCALPHA)
                s.fill((255, 255, 255, 128))
                gamescreen.blit(s, (0, 0))
                gamescreen.blit(win_surface, win_rect)

                pygame.display.flip()
                waiting = True
                wait_start = pygame.time.get_ticks()
                while waiting:
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            waiting = False
                            running = False
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                waiting = False
                                running = False
                    if pygame.time.get_ticks() - wait_start > 5000:
                        waiting = False
                        running = False
                
            except Exception as e:
                print(f"你去死吧：{e}")
    pygame.display.flip()
    
    clock.tick(target_fps)

pygame.quit()
sys.exit()
