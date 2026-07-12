import pygame
import math
import random
import sys
import socket
import threading
import json
import time
import uuid
import argparse

from log_interface import get_logger, start_log_server, stop_log_server

log = get_logger("Game")
net_log = get_logger("Network")

WIDTH, HEIGHT = 800, 600
FPS = 60


class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.thrust = 0
        self.dead = False

    def update(self, dt):
        self.vx += math.cos(self.angle) * self.thrust * dt
        self.vy += math.sin(self.angle) * self.thrust * dt
        self.vx *= 0.995
        self.vy *= 0.995
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surf):
        pts = []
        heading = (math.cos(self.angle), math.sin(self.angle))
        right = (math.cos(self.angle + 2.5), math.sin(self.angle + 2.5))
        left = (math.cos(self.angle - 2.5), math.sin(self.angle - 2.5))
        scale = 12
        pts.append((self.x + heading[0] * scale, self.y + heading[1] * scale))
        pts.append((self.x + right[0] * scale * 0.7, self.y + right[1] * scale * 0.7))
        pts.append((self.x + left[0] * scale * 0.7, self.y + left[1] * scale * 0.7))
        pygame.draw.polygon(surf, (180, 200, 255), pts)


class Bullet:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 2.0

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surf):
        pygame.draw.circle(surf, (255, 240, 120), (int(self.x), int(self.y)), 3)


class Enemy:
    def __init__(self, x=None, y=None, vx=None, vy=None, r=None):
        if x is None:
            self.x = random.uniform(0, WIDTH)
            self.y = random.uniform(0, HEIGHT)
            ang = random.uniform(0, math.tau)
            self.vx = math.cos(ang) * random.uniform(20, 80)
            self.vy = math.sin(ang) * random.uniform(20, 80)
            self.r = random.randint(10, 26)
        else:
            self.x = x
            self.y = y
            self.vx = vx
            self.vy = vy
            self.r = r

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.x %= WIDTH
        self.y %= HEIGHT

    def draw(self, surf):
        pygame.draw.circle(surf, (200, 120, 120), (int(self.x), int(self.y)), self.r)

    def to_dict(self):
        return {'x': self.x, 'y': self.y, 'vx': self.vx, 'vy': self.vy, 'r': self.r}


class NetworkClient:
    """Simple UDP relay client with enemy sync. Lowest ID client is host."""
    def __init__(self, server_host, server_port, player_ref, bullets_ref, others_ref, enemies_ref):
        self.server = (server_host, server_port)
        self.player = player_ref
        self.bullets = bullets_ref
        self.others = others_ref
        self.enemies = enemies_ref
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(1.0)
        self.id = str(uuid.uuid4())[:8]
        self.running = True
        self.lock = threading.Lock()
        self.listen_thread = threading.Thread(target=self._listen, daemon=True)
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.listen_thread.start()
        self.send_thread.start()
        self.is_host = False

    def _listen(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(8192)
            except socket.timeout:
                continue
            except Exception:
                continue
            try:
                msg = json.loads(data.decode('utf8'))
            except Exception:
                continue
            sender = msg.get('id')
            if sender == self.id:
                continue
            mtype = msg.get('type')
            if mtype == 'state':
                with self.lock:
                    self.others[sender] = {'x': msg.get('x',0), 'y': msg.get('y',0), 'angle': msg.get('angle',0)}
                # Host election: lowest ID wins
                all_ids = [self.id] + list(self.others.keys())
                self.is_host = (min(all_ids) == self.id)
            elif mtype == 'shoot':
                bx = msg.get('x')
                by = msg.get('y')
                bvx = msg.get('vx')
                bvy = msg.get('vy')
                if bx is not None:
                    with self.lock:
                        self.bullets.append(Bullet(bx, by, bvx, bvy))
            elif mtype == 'enemies':
                # Apply host's enemy state
                with self.lock:
                    enemy_list = msg.get('enemies', [])
                    if len(enemy_list) == len(self.enemies):
                        for i, ed in enumerate(enemy_list):
                            if i < len(self.enemies):
                                e = self.enemies[i]
                                e.x = ed.get('x', e.x)
                                e.y = ed.get('y', e.y)
                                e.vx = ed.get('vx', e.vx)
                                e.vy = ed.get('vy', e.vy)

    def _send_loop(self):
        while self.running:
            try:
                # Player state
                payload = {'type':'state','id':self.id,'x':self.player.x,'y':self.player.y,
                           'angle':self.player.angle,'vx':self.player.vx,'vy':self.player.vy}
                self.sock.sendto(json.dumps(payload).encode('utf8'), self.server)

                # Host broadcasts enemies
                if self.is_host and random.random() < 0.3:
                    enemy_data = [e.to_dict() for e in self.enemies]
                    epayload = {'type':'enemies', 'id':self.id, 'enemies': enemy_data}
                    self.sock.sendto(json.dumps(epayload).encode('utf8'), self.server)
            except Exception:
                pass
            time.sleep(0.1)

    def send_shoot(self, bx, by, bvx, bvy):
        try:
            payload = {'type':'shoot','id':self.id,'x':bx,'y':by,'vx':bvx,'vy':bvy}
            self.sock.sendto(json.dumps(payload).encode('utf8'), self.server)
        except Exception:
            pass

    def close(self):
        self.running = False
        try:
            self.listen_thread.join(timeout=0.5)
            self.send_thread.join(timeout=0.5)
        except Exception:
            pass


def main(server_host=None, server_port=50000, log_port=9000):
    start_log_server(port=log_port)
    log.info("Game starting")

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("XPilot (minimal) - Python")
    clock = pygame.time.Clock()
    log.info(f"Display initialized: {WIDTH}x{HEIGHT} @ {FPS} FPS")

    player = Player(WIDTH // 2, HEIGHT // 2)
    bullets = []
    enemies = [Enemy() for _ in range(6)]
    score = 0
    shoot_cool = 0.0

    remote_players = {}
    netclient = None
    if server_host:
        try:
            netclient = NetworkClient(server_host, server_port, player, bullets, remote_players, enemies)
            net_log.info(f"Connected to server {server_host}:{server_port} (id={netclient.id})")
        except Exception as e:
            net_log.error(f"Network disabled: {e}")

    font = pygame.font.SysFont(None, 24)

    prev_dead = player.dead
    prev_score = score
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                log.info("Quit event received")
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    log.info("Escape pressed, exiting")
                    running = False
                if player.dead and event.key == pygame.K_r:
                    player = Player(WIDTH // 2, HEIGHT // 2)
                    bullets = []
                    enemies = [Enemy() for _ in range(6)]
                    score = 0
                    log.info("Player respawned")

        keys = pygame.key.get_pressed()
        player.thrust = 0
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            player.thrust = 200
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            player.angle -= 3 * dt
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            player.angle += 3 * dt

        shoot_cool -= dt
        if keys[pygame.K_SPACE] and shoot_cool <= 0 and not player.dead:
            shoot_cool = 0.15
            speed = 400
            bx = player.x + math.cos(player.angle) * 16
            by = player.y + math.sin(player.angle) * 16
            bvx = player.vx + math.cos(player.angle) * speed
            bvy = player.vy + math.sin(player.angle) * speed
            bullets.append(Bullet(bx, by, bvx, bvy))
            if netclient:
                netclient.send_shoot(bx, by, bvx, bvy)

        if not player.dead:
            player.update(dt)

        for b in bullets[:]:
            b.update(dt)
            if b.life <= 0:
                bullets.remove(b)

        # Enemy simulation: only host runs physics (others sync via network)
        if not netclient or netclient.is_host:
            for e in enemies[:]:
                e.update(dt)

        # collisions (local for responsiveness)
        if not player.dead:
            for e in enemies:
                if math.hypot(player.x - e.x, player.y - e.y) < e.r + 8:
                    player.dead = True

        for b in bullets[:]:
            for e in enemies[:]:
                if math.hypot(b.x - e.x, b.y - e.y) < e.r:
                    try:
                        enemies.remove(e)
                        bullets.remove(b)
                    except ValueError:
                        pass
                    score += 10
                    enemies.append(Enemy())
                    break

        if player.dead and not prev_dead:
            log.warning("Player died!")
        prev_dead = player.dead

        if score != prev_score:
            log.info(f"Score: {score}")
            prev_score = score

        # draw
        screen.fill((12, 12, 24))
        for e in enemies:
            e.draw(screen)
        for b in bullets:
            b.draw(screen)
        if not player.dead:
            player.draw(screen)
        else:
            txt = font.render("You Died - press R to restart", True, (220, 220, 220))
            screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 12))

        with (netclient.lock if netclient else threading.Lock()):
            for pid, info in remote_players.items():
                rx = info.get('x', 0)
                ry = info.get('y', 0)
                ang = info.get('angle', 0)
                pts = []
                heading = (math.cos(ang), math.sin(ang))
                right = (math.cos(ang + 2.5), math.sin(ang + 2.5))
                left = (math.cos(ang - 2.5), math.sin(ang - 2.5))
                scale = 10
                pts.append((rx + heading[0] * scale, ry + heading[1] * scale))
                pts.append((rx + right[0] * scale * 0.7, ry + right[1] * scale * 0.7))
                pts.append((rx + left[0] * scale * 0.7, ry + left[1] * scale * 0.7))
                pygame.draw.polygon(screen, (120, 220, 140), pts)

        hud = font.render(f"Score: {score}", True, (200, 200, 200))
        screen.blit(hud, (8, 8))

        pygame.display.flip()

    log.info("Game shutting down")
    pygame.quit()
    if netclient:
        netclient.close()
    stop_log_server()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="XPilot minimal with optional networking")
    parser.add_argument("--server", help="server host to connect to (run net_server.py separately)")
    parser.add_argument("--port", type=int, default=50000, help="server UDP port")
    parser.add_argument("--log-port", type=int, default=9000, help="TCP port for external log terminal (default: 9000)")
    args = parser.parse_args()
    try:
        main(args.server, args.port, args.log_port)
    except Exception as e:
        log.critical(f"Fatal error: {e}")
        pygame.quit()
        sys.exit(1)