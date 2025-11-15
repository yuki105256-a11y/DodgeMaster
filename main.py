# main.py - Cartoon-style Kivy Dodge Master (improved & APK-ready)
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, RoundedRectangle, Line
from kivy.uix.widget import Widget
from kivy.uix.image import Image as KivyImage
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.properties import NumericProperty, BooleanProperty, ListProperty
from kivy.core.audio import SoundLoader
from kivy.utils import get_color_from_hex
import random, math, os, time

# logical resolution
WIDTH, HEIGHT = 720, 1280

# Assets folder
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Colors (cartoon palette)
WHITE = (1,1,1,1)
BLACK = (0.02,0.02,0.02,1)
BG_TOP = get_color_from_hex("#28538a")
BG_BOTTOM = get_color_from_hex("#5bd07a")
PLAYER_COLOR = (60/255.0,140/255.0,220/255.0,1)

PLAYER_RADIUS = 34
PLAYER_BASE_SPEED = 520.0
PLAYER_PULSE_SPEED = 2.6

JOYSTICK_BASE_POS = (120, 200)
JOYSTICK_BASE_RADIUS = 100
JOYSTICK_KNOB_RADIUS = 46

BUTTON_WIDTH = 220
BUTTON_HEIGHT = 140

SPAWN_BASE_DELAY = 0.70
SPAWN_MIN_DELAY = 0.18

DIFFICULTY_SETTINGS = {
    "Easy": {"spawn_mult": 1.35, "speed_mult": 0.85},
    "Normal": {"spawn_mult": 1.0, "speed_mult": 1.0},
    "Hard": {"spawn_mult": 0.75, "speed_mult": 1.3},
}

HIGHSCORE_FILE = "highscore.txt"

def clamp(v,a,b): return max(a,min(b,v))

def circle_rect_collision(cx,cy,r,rect):
    rx,ry,rw,rh = rect
    closest_x = clamp(cx, rx, rx+rw)
    closest_y = clamp(cy, ry, ry+rh)
    dx = cx - closest_x; dy = cy - closest_y
    return dx*dx + dy*dy < r*r

class Particle:
    def __init__(self,x,y,vx,vy,lifetime,color,size):
        self.x=x; self.y=y; self.vx=vx; self.vy=vy; self.lifetime=lifetime; self.age=0; self.color=color; self.size=size
    def update(self,dt):
        self.age+=dt; self.x+=self.vx*dt; self.y+=self.vy*dt; self.vy+=420*dt

class Enemy:
    def __init__(self,x,y,size,speed,typ="block",amp=0,freq=0):
        self.x=x; self.y=y; self.size=size; self.speed=speed; self.type=typ; self.amp=amp; self.freq=freq; self.offset=random.random()*1000.0
    def update(self,dt):
        self.y+=self.speed*dt
        if self.type=="zigzag":
            self.x += math.sin((time.time()+self.offset)*self.freq)*self.amp*dt
    def get_rect(self):
        return (self.x-self.size/2, self.y-self.size/2, self.size, self.size)

class Player:
    def __init__(self,x,y):
        self.x=x; self.y=y; self.radius=PLAYER_RADIUS; self.target_x=x; self.target_y=y; self.speed=PLAYER_BASE_SPEED; self.pulse=1.0
    def update(self,dt):
        dx=self.target_x-self.x; dy=self.target_y-self.y; dist=math.hypot(dx,dy)
        if dist>1:
            move=min(self.speed*dt,dist); self.x += dx/dist*move; self.y += dy/dist*move
        self.pulse = 0.9 + 0.18 * math.sin(2*math.pi*PLAYER_PULSE_SPEED * time.time())
    def set_target(self,tx,ty):
        self.target_x = clamp(tx,self.radius,WIDTH-self.radius)
        self.target_y = clamp(ty,self.radius,HEIGHT-self.radius-200)

class GameWidget(Widget):
    score = NumericProperty(0)
    highscore = NumericProperty(0)
    paused = BooleanProperty(False)
    game_over = BooleanProperty(False)

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.player = Player(WIDTH//2, HEIGHT-320)
        self.enemies = []; self.particles = []; self.spawn_timer=0; self.score=0; self.highscore=self.load_highscore()
        self.joystick_active=False; self.joystick_knob_pos=[JOYSTICK_BASE_POS[0], JOYSTICK_BASE_POS[1]]
        self.settings={"sound":True,"difficulty":"Normal","joystick_sensitivity":1.0}
        # load assets if present
        self.player_img = None; self.enemy_img=None; self.bg_img=None
        try:
            from kivy.core.image import Image as CoreImage
            p = os.path.join(ASSETS_DIR,"player.png")
            e = os.path.join(ASSETS_DIR,"enemy.png")
            b = os.path.join(ASSETS_DIR,"background.png")
            if os.path.exists(p): self.player_img = CoreImage(p).texture
            if os.path.exists(e): self.enemy_img = CoreImage(e).texture
            if os.path.exists(b): self.bg_img = CoreImage(b).texture
        except Exception:
            pass
        # sound
        self.explosion_sound = None
        try:
            snd = SoundLoader.load(os.path.join(ASSETS_DIR,"explosion.wav"))
            if snd: self.explosion_sound = snd
        except Exception:
            pass
        Clock.schedule_interval(self.update, 1.0/60.0)

    def load_highscore(self):
        try:
            path = os.path.join(App.get_running_app().user_data_dir, HIGHSCORE_FILE)
            with open(path,"r") as f: return int(f.read().strip())
        except Exception: return 0
    def save_highscore(self,v):
        try:
            path = os.path.join(App.get_running_app().user_data_dir, HIGHSCORE_FILE)
            with open(path,"w") as f: f.write(str(int(v)))
        except Exception: pass

    def spawn_enemy(self,difficulty):
        ds=DIFFICULTY_SETTINGS.get(difficulty,DIFFICULTY_SETTINGS["Normal"]); speed_base=160.0*ds["speed_mult"]
        r=random.random(); x=random.randint(60, WIDTH-60)
        if r<0.55: size=random.randint(48,86); e=Enemy(x,-60,size,speed_base*random.uniform(0.9,1.35),"block")
        elif r<0.78: w=random.randint(36,56); e=Enemy(x,-40,w,speed_base*random.uniform(1.6,2.6),"missile")
        else: size=random.randint(46,72); amp=random.randint(60,140); freq=random.uniform(1.2,3.0); e=Enemy(x,-80,size,speed_base*random.uniform(0.9,1.4),"zigzag",amp,freq)
        self.enemies.append(e)

    def spawn_explosion(self,x,y,count=18):
        for i in range(count):
            ang=random.random()*2*math.pi; spd=random.uniform(140,440)
            vx=math.cos(ang)*spd; vy=math.sin(ang)*spd*0.7; lifetime=random.uniform(0.45,1.05); size=random.uniform(4,12)
            c=random.choice([(255,140,60),(245,210,70),(230,60,60)])
            self.particles.append(Particle(x,y,vx,vy,lifetime,c,size))
        if self.explosion_sound:
            try: self.explosion_sound.play()
            except Exception: pass

    def update(self,dt):
        if self.paused or self.game_over: 
            self.canvas.ask_update(); return
        ds=DIFFICULTY_SETTINGS.get(self.settings["difficulty"], DIFFICULTY_SETTINGS["Normal"])
        spawn_delay = max(SPAWN_MIN_DELAY, SPAWN_BASE_DELAY * ds["spawn_mult"]); self.spawn_timer += dt
        if self.spawn_timer >= spawn_delay: self.spawn_timer = 0; self.spawn_enemy(self.settings["difficulty"])
        self.player.update(dt)
        new_enemies=[]
        for e in self.enemies:
            e.update(dt)
            if e.y - e.size/2 > HEIGHT+120:
                self.score += 1
                if self.score > self.highscore: self.highscore = self.score; self.save_highscore(self.highscore)
            else: new_enemies.append(e)
        self.enemies[:] = new_enemies
        new_particles=[]
        for p in self.particles:
            p.update(dt)
            if p.age < p.lifetime: new_particles.append(p)
        self.particles[:] = new_particles
        for e in self.enemies:
            if circle_rect_collision(self.player.x, self.player.y, self.player.radius, e.get_rect()):
                self.spawn_explosion(self.player.x, self.player.y, count=28); self.game_over=True; break
        self.canvas.ask_update()

    def on_touch_down(self,touch):
        mx=touch.x*(WIDTH/self.width); my=touch.y*(HEIGHT/self.height)
        # pause region (top-right)
        if (mx>WIDTH-180 and mx<WIDTH-40 and my>HEIGHT-120 and my<HEIGHT-40) and not self.game_over:
            self.paused = not self.paused; return True
        if (mx>40 and mx<40+BUTTON_WIDTH and my>40 and my<40+BUTTON_HEIGHT) and not self.game_over:
            self.player.set_target(self.player.x-140,self.player.y); return True
        if (mx>WIDTH-BUTTON_WIDTH-40 and mx<WIDTH-40 and my>40 and my<40+BUTTON_HEIGHT) and not self.game_over:
            self.player.set_target(self.player.x+140,self.player.y); return True
        jb_x,jb_y = JOYSTICK_BASE_POS; dx=mx-jb_x; dy=my-jb_y
        if dx*dx+dy*dy <= (JOYSTICK_BASE_RADIUS*1.7)**2 and not self.game_over:
            self.joystick_active=True; maxd=JOYSTICK_BASE_RADIUS-JOYSTICK_KNOB_RADIUS-8; dist=math.hypot(dx,dy)
            if dist>maxd and dist>0: dx=dx/dist*maxd; dy=dy/dist*maxd
            self.joystick_knob_pos=[jb_x+dx,jb_y+dy]; nx=(self.joystick_knob_pos[0]-jb_x)/maxd
            tx=self.player.x+nx*380*self.settings["joystick_sensitivity"]; self.player.set_target(tx,self.player.y); return True
        return super().on_touch_down(touch)

    def on_touch_move(self,touch):
        if not self.joystick_active or self.paused or self.game_over: return super().on_touch_move(touch)
        mx=touch.x*(WIDTH/self.width); my=touch.y*(HEIGHT/self.height); jb_x,jb_y=JOYSTICK_BASE_POS
        dx=mx-jb_x; dy=my-jb_y; maxd=JOYSTICK_BASE_RADIUS-JOYSTICK_KNOB_RADIUS-8; dist=math.hypot(dx,dy)
        if dist>maxd and dist>0: dx=dx/dist*maxd; dy=dy/dist*maxd
        self.joystick_knob_pos=[jb_x+dx,jb_y+dy]; nx=(self.joystick_knob_pos[0]-jb_x)/maxd
        tx=self.player.x+nx*380*self.settings["joystick_sensitivity"]; self.player.set_target(tx,self.player.y); return True

    def on_touch_up(self,touch):
        if self.joystick_active: self.joystick_active=False; self.joystick_knob_pos=[JOYSTICK_BASE_POS[0],JOYSTICK_BASE_POS[1]]; self.player.set_target(self.player.x,self.player.y); return True
        return super().on_touch_up(touch)

    def draw_frame(self):
        # we clear and redraw; called by outer layout
        self.canvas.clear()
        with self.canvas:
            # background (image or gradient)
            if self.bg_img:
                Rectangle(texture=self.bg_img, pos=(0,0), size=(self.width,self.height))
            else:
                Color(*BG_TOP); Rectangle(pos=(0,self.height/2), size=(self.width,self.height/2))
                Color(*BG_BOTTOM); Rectangle(pos=(0,0), size=(self.width,self.height/2))
            # enemies
            for e in self.enemies:
                ex=(e.x-e.size/2)*(self.width/WIDTH); ey=(e.y-e.size/2)*(self.height/HEIGHT)
                ew=e.size*(self.width/WIDTH); eh=e.size*(self.height/HEIGHT)
                if self.enemy_img:
                    Rectangle(texture=self.enemy_img, pos=(ex,ey), size=(ew,eh))
                else:
                    Color(230/255.0,60/255.0,60/255.0,1); RoundedRectangle(pos=(ex,ey), size=(ew,eh), radius=[8])
            # particles
            for p in self.particles:
                t=clamp(1.0 - p.age/p.lifetime,0,1); Color(p.color[0]/255.0,p.color[1]/255.0,p.color[2]/255.0,t)
                Ellipse(pos=((p.x-p.size)*(self.width/WIDTH),(p.y-p.size)*(self.height/HEIGHT)), size=(p.size*2*(self.width/WIDTH),p.size*2*(self.height/HEIGHT)))
            # player
            px=self.player.x*(self.width/WIDTH); py=self.player.y*(self.height/HEIGHT)
            r=int(self.player.radius*self.player.pulse)*(self.width/WIDTH)
            if self.player_img:
                Rectangle(texture=self.player_img, pos=(px-r,py-r), size=(r*2,r*2))
            else:
                Color(*PLAYER_COLOR); Ellipse(pos=(px-r,py-r), size=(r*2,r*2))
            # joystick and buttons
            Color(0.14,0.14,0.14,1); jb_x=JOYSTICK_BASE_POS[0]*(self.width/WIDTH); jb_y=JOYSTICK_BASE_POS[1]*(self.height/HEIGHT)
            Ellipse(pos=(jb_x-JOYSTICK_BASE_RADIUS*(self.width/WIDTH), jb_y-JOYSTICK_BASE_RADIUS*(self.height/HEIGHT)), size=(JOYSTICK_BASE_RADIUS*2*(self.width/WIDTH),JOYSTICK_BASE_RADIUS*2*(self.height/HEIGHT)))
            Color(0.7,0.7,0.7,1); kx=self.joystick_knob_pos[0]*(self.width/WIDTH); ky=self.joystick_knob_pos[1]*(self.height/HEIGHT)
            Ellipse(pos=(kx-JOYSTICK_KNOB_RADIUS*(self.width/WIDTH), ky-JOYSTICK_KNOB_RADIUS*(self.height/HEIGHT)), size=(JOYSTICK_KNOB_RADIUS*2*(self.width/WIDTH),JOYSTICK_KNOB_RADIUS*2*(self.height/HEIGHT)))

class GameRoot(FloatLayout):
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.game = GameWidget(size_hint=(1,1), pos=(0,0))
        self.add_widget(self.game)
        # labels and buttons
        self.score_label = Label(text=f"Score: {self.game.score}", pos=(28, self.height-50), size_hint=(None,None))
        self.best_label = Label(text=f"Best: {self.game.highscore}", pos=(28, self.height-90), size_hint=(None,None))
        self.add_widget(self.score_label); self.add_widget(self.best_label)
        self.pause_btn = Button(text='⏸', size_hint=(None,None), size=(80,40), pos=(self.width-100,self.height-60))
        self.pause_btn.bind(on_release=self.toggle_pause); self.add_widget(self.pause_btn)
        self.left_btn = Button(text='LEFT', size_hint=(None,None), size=(120,60), pos=(40,40)); self.left_btn.bind(on_release=lambda *a: self.game.player.set_target(self.game.player.x-140,self.game.player.y)); self.add_widget(self.left_btn)
        self.right_btn = Button(text='RIGHT', size_hint=(None,None), size=(120,60), pos=(self.width-160,40)); self.right_btn.bind(on_release=lambda *a: self.game.player.set_target(self.game.player.x+140,self.game.player.y)); self.add_widget(self.right_btn)
        self.restart_btn = Button(text='RESTART', size_hint=(None,None), size=(160,60), pos=(self.width/2-80,self.height/2-30), opacity=0)
        self.restart_btn.bind(on_release=self.on_restart); self.add_widget(self.restart_btn)
        Clock.schedule_interval(self._ui_sync, 1.0/10.0)
        # call game draw each frame
        Clock.schedule_interval(lambda dt: self.game.draw_frame(), 1.0/60.0)

    def _ui_sync(self,dt):
        self.score_label.text = f"Score: {self.game.score}"; self.best_label.text = f"Best: {self.game.highscore}"
        if self.game.game_over: self.restart_btn.opacity = 1
        else: self.restart_btn.opacity = 0
    def toggle_pause(self,*a): self.game.paused = not self.game.paused
    def on_restart(self,*a): self.game.reset(); self.restart_btn.opacity = 0

class DodgeApp(App):
    def build(self):
        self.user_data_dir = getattr(self, 'user_data_dir', None) or os.path.join(os.path.expanduser('~'), '.dodge_master')
        os.makedirs(self.user_data_dir, exist_ok=True)
        return GameRoot()

if __name__=='__main__':
    DodgeApp().run()
