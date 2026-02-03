import pygame
import math
import requests
import threading
import time
import csv
from plyer import gps, compass

# --- پیکربندی استایل ---
COLOR_NEON = (0, 255, 170)
COLOR_NEON_DIM = (0, 80, 60)
COLOR_CRITICAL = (255, 50, 50)
COLOR_BG = (2, 8, 6)
FONT_FILE = "font.ttf"

# --- متغیرهای دیتابیس و وضعیت ---
field_logs = []
current_data = {"loc_des": "", "activity": "", "tag": "", "note": "", "issue": ""}
last_coords = "00.000 , 00.000"
bearing = 0
display_name = "SEARCHING..."
splash_active = True
log_view_active = False
selected_index = -1

# --- توابع سیستمی (GPS & Compass) ---
def on_location(**kwargs):
    global last_coords, display_name
    lat, lon = kwargs['lat'], kwargs['lon']
    last_coords = f"{lat:.4f} N, {lon:.4f} E"
    # دریافت نام منطقه در پس‌زمینه
    threading.Thread(target=fetch_area_name, args=(lat, lon), daemon=True).start()

def fetch_area_name(lat, lon):
    global display_name
    try:
        res = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json", timeout=5).json()
        display_name = (res.get('address', {}).get('suburb') or res.get('address', {}).get('city') or "SITE SECTOR").upper()
    except: display_name = "OFFLINE SECTOR"

def on_compass(values):
    global bearing
    if values: bearing = values[0]

try:
    gps.configure(on_location=on_location)
    gps.start()
    compass.enable()
except: pass

# --- کلاس انیمیشن امواج ---
class Pulse:
    def __init__(self, x, y, max_r, speed):
        self.x, self.y, self.max_r, self.speed = x, y, max_r, speed
        self.r, self.alpha = 10, 200
    def update(self):
        self.r += self.speed
        self.alpha = max(0, self.alpha - (self.speed * 200 / self.max_r))
    def draw(self, surf):
        s = pygame.Surface((self.r*2, self.r*2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*COLOR_NEON, int(self.alpha)), (self.r, self.r), self.r, 2)
        surf.blit(s, (self.x - self.r, self.y - self.r))

# --- شروع موتور گرافیکی ---
pygame.init()
info = pygame.display.Info()
WIDTH, HEIGHT = info.current_w, info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
clock = pygame.time.Clock()

# بارگذاری فونت‌ها
try:
    f_huge = pygame.font.Font(FONT_FILE, WIDTH//10)
    f_mid = pygame.font.Font(FONT_FILE, WIDTH//20)
    f_small = pygame.font.Font(FONT_FILE, WIDTH//30)
except:
    f_huge = pygame.font.SysFont("Arial", 50, True)
    f_mid = pygame.font.SysFont("Arial", 30)
    f_small = pygame.font.SysFont("Arial", 20)

pulses = []
start_time = time.time()

# --- حلقه اصلی ---
while True:
    screen.fill(COLOR_BG)
    mx, my = WIDTH // 2, HEIGHT // 3 + 50 # مرکز رادار

    for event in pygame.event.get():
        if event.type == pygame.QUIT: pygame.quit(); exit()
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not splash_active:
                # دکمه ثبت (CAPTURE)
                if pygame.Rect(WIDTH//2-100, HEIGHT-220, 200, 60).collidepoint(event.pos):
                    row = [time.strftime("%Y-%m-%d %H:%M"), last_coords, current_data["loc_des"] or "-", 
                           current_data["activity"] or "-", current_data["tag"] or "-", 
                           current_data["note"] or "-", current_data["issue"] or "-"]
                    field_logs.append(row)
                # دکمه خروجی CSV
                if pygame.Rect(WIDTH-120, HEIGHT-60, 100, 40).collidepoint(event.pos):
                    fname = f"GA_REPORT_{time.strftime('%H%M')}.csv"
                    with open(fname, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Date & Time", "Geo", "Loc Des", "Activity", "Tag", "Note", "Remark"])
                        writer.writerows(field_logs)

    # ۱. صفحه ورودی (Splash Screen)
    if splash_active:
        if time.time() - start_time < 3:
            txt = f_huge.render("GA RADAR", True, COLOR_NEON)
            git = f_small.render("github.com/arshsyst", True, COLOR_NEON_DIM)
            screen.blit(txt, txt.get_rect(center=(WIDTH//2, HEIGHT//2)))
            screen.blit(git, git.get_rect(center=(WIDTH//2, HEIGHT//2 + 60)))
        else: splash_active = False
        pygame.display.flip()
        continue

    # ۲. رادار و قطب‌نما
    if pygame.time.get_ticks() % 60 == 0: pulses.append(Pulse(mx, my, 250, 4))
    for p in pulses[:]:
        p.update(); p.draw(screen)
        if p.alpha <= 0: pulses.remove(p)
    
    # رسم حروف قطب‌نما (N, S, E, W)
    for label, angle in [("N", 0), ("E", 90), ("S", 180), ("W", 270)]:
        rad = math.radians(angle - bearing)
        tx = mx + 220 * math.sin(rad)
        ty = my - 220 * math.cos(rad)
        screen.blit(f_small.render(label, True, COLOR_NEON), (tx-10, ty-10))

    # ۳. نمایش اطلاعات زنده
    screen.blit(f_mid.render(display_name, True, COLOR_NEON), (40, HEIGHT//2 + 50))
    screen.blit(f_small.render(last_coords, True, COLOR_NEON_DIM), (40, HEIGHT//2 + 90))

    # ۴. دکمه‌ها (UI پایین صفحه)
    pygame.draw.rect(screen, COLOR_NEON, (WIDTH//2-100, HEIGHT-220, 200, 60), 2, border_radius=10)
    screen.blit(f_small.render("CAPTURE & LOG", True, COLOR_NEON), (WIDTH//2-80, HEIGHT-200))
    
    pygame.draw.rect(screen, COLOR_NEON_DIM, (WIDTH-120, HEIGHT-60, 100, 40), 1)
    screen.blit(f_small.render("CSV", True, COLOR_NEON_DIM), (WIDTH-85, HEIGHT-50))

    pygame.display.flip()
    clock.tick(30)
