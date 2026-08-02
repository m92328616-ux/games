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

import pvp_system

from log_interface import (
    get_logger,
    parse_forward_address,
    set_log_level,
    start_log_forward,
    start_log_server,
    stop_log_forward,
    stop_log_server,
)

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
        self.hp = pvp_system.PLAYER_MAX_HP
        self.max_hp = pvp_system.PLAYER_MAX_HP

    def respawn(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        self.angle = 0
        self.thrust = 0
        self.dead = False
        self.hp = pvp_system.PLAYER_MAX_HP

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
    def __init__(self, x, y, vx, vy, owner=None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = 2.0
        self.owner = owner

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
    """Simple UDP relay client with enemy sync and PvP. Lowest ID client is host."""
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
        # ── PvP state (issue #10) ─────────────────────────────────────────
        self.pvp_mode = False
        self.players_hp = {}     # host-authoritative {id: {hp,maxHp,dead}}
        self.ram_cooldowns = {}  # {remoteId: timeLeft} to avoid repeated ram damage

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
                    info = self.others.get(sender, {})
                    info['x'] = msg.get('x', 0)
                    info['y'] = msg.get('y', 0)
                    info['angle'] = msg.get('angle', 0)
                    info['dead'] = bool(msg.get('dead', False))
                    if 'hp' in msg:
                        info['hp'] = msg['hp']
                    if 'maxHp' in msg:
                        info['maxHp'] = msg['maxHp']
                    self.others[sender] = info
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
                        self.bullets.append(Bullet(bx, by, bvx, bvy, owner=sender))
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
            elif mtype == 'player_hit':
                # A non-host reports damage it dealt; only the host applies it.
                if not self.pvp_mode or not self.is_host:
                    continue
                target = msg.get('target')
                attacker = msg.get('id')
                dmg = msg.get('dmg', 1)
                if target:
                    self._host_apply_damage(target, dmg, attacker)
            elif mtype == 'player_hp':
                # Host broadcasts authoritative HP/elimination state.
                if not self.pvp_mode:
                    continue
                pid = msg.get('id')
                if not pid:
                    continue
                hp = msg.get('hp', 0)
                dead = bool(msg.get('dead', False))
                killer = msg.get('killer', '')
                if pid == self.id:
                    with self.lock:
                        self.player.hp = hp
                        self.player.dead = dead
                    if dead:
                        log.warning(f"You were killed by {killer or 'unknown'}")
                else:
                    with self.lock:
                        info = self.others.get(pid)
                        if info:
                            info['hp'] = hp
                            info['dead'] = dead
                if self.is_host and pid in self.players_hp:
                    self.players_hp[pid]['hp'] = hp
                    self.players_hp[pid]['dead'] = dead
                if dead and pid != self.id:
                    log.warning(f"{killer or 'unknown'} killed {pid}")
            elif mtype == 'player_respawn':
                # A player restarted; the host resets its HP record and
                # broadcasts the fresh (alive) state to everyone.
                if not self.pvp_mode or not self.is_host:
                    continue
                pid = msg.get('id')
                if not pid:
                    continue
                st = pvp_system.create_player_hp_state()
                self.players_hp[pid] = st
                self.send_player_hp(pid, st['hp'], st['dead'], '')

    def _host_apply_damage(self, target, dmg, killer):
        """Host-authoritative damage application (PvP)."""
        if not self.pvp_mode or not self.is_host:
            return
        with self.lock:
            st = self.players_hp.get(target)
            if st is None:
                st = pvp_system.create_player_hp_state()
                self.players_hp[target] = st
            res = pvp_system.apply_player_damage(st, dmg)
            hp, dead = st['hp'], st['dead']
            if target == self.id:
                self.player.hp = hp
                self.player.dead = dead
            else:
                info = self.others.get(target)
                if info:
                    info['hp'] = hp
                    info['dead'] = dead
        self.send_player_hp(target, hp, dead, killer or '')
        if res['lethal']:
            log.warning(f"{killer or 'unknown'} killed {target}")

    def report_hit(self, target, dmg, attacker):
        """Report a PvP hit: apply locally if host, else send to the host."""
        if not self.pvp_mode:
            return
        if self.is_host:
            self._host_apply_damage(target, dmg, attacker)
        else:
            try:
                payload = {'type': 'player_hit', 'id': attacker, 'target': target, 'dmg': dmg}
                self.sock.sendto(json.dumps(payload).encode('utf8'), self.server)
            except Exception:
                pass

    def send_player_hp(self, pid, hp, dead, killer):
        try:
            payload = {'type': 'player_hp', 'id': pid, 'hp': hp,
                       'dead': dead, 'killer': killer or ''}
            self.sock.sendto(json.dumps(payload).encode('utf8'), self.server)
        except Exception:
            pass

    def send_player_respawn(self):
        try:
            payload = {'type': 'player_respawn', 'id': self.id}
            self.sock.sendto(json.dumps(payload).encode('utf8'), self.server)
        except Exception:
            pass

    def respawn_local(self, spawn_x, spawn_y):
        """Respawn on a fair PvP spawn point and reset the host's HP record."""
        with self.lock:
            self.player.respawn(spawn_x, spawn_y)
        if self.pvp_mode:
            if self.is_host:
                st = pvp_system.create_player_hp_state()
                self.players_hp[self.id] = st
                self.send_player_hp(self.id, st['hp'], st['dead'], '')
            else:
                self.send_player_respawn()

    def _send_loop(self):
        while self.running:
            try:
                # Player state
                payload = {'type':'state','id':self.id,'x':self.player.x,'y':self.player.y,
                           'angle':self.player.angle,'vx':self.player.vx,'vy':self.player.vy,
                           'dead':self.player.dead,'hp':self.player.hp,'maxHp':self.player.max_hp}
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


def main(server_host=None, server_port=50000):
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
                    if netclient and netclient.pvp_mode:
                        sp = pvp_system.spawn_point_for_id(netclient.id, WIDTH, HEIGHT)
                        netclient.respawn_local(sp['x'], sp['y'])
                    else:
                        player.respawn(WIDTH // 2, HEIGHT // 2)
                    bullets = []
                    enemies = [Enemy() for _ in range(6)]
                    score = 0
                    log.info("Player respawned")
                if netclient and event.key == pygame.K_v:
                    netclient.pvp_mode = not netclient.pvp_mode
                    if netclient.pvp_mode:
                        sp = pvp_system.spawn_point_for_id(netclient.id, WIDTH, HEIGHT)
                        netclient.respawn_local(sp['x'], sp['y'])
                        log.info("PvP mode enabled")
                    else:
                        log.info("PvP mode disabled")

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

        # PvP combat (issue #10). Only the bullet's owner reports a hit, so a
        # single shot never deals double damage (both shooter and target would
        # otherwise detect the same collision).
        if netclient and netclient.pvp_mode:
            for b in bullets:
                if b.owner:
                    continue  # remote bullet: its owner reports it
                for pid, info in list(remote_players.items()):
                    if info.get('dead'):
                        continue
                    if pvp_system.distance_between(b.x, b.y, info['x'], info['y'], WIDTH, HEIGHT) < pvp_system.BULLET_HIT_RADIUS:
                        netclient.report_hit(pid, 1, netclient.id)
                        break
            if not player.dead:
                for pid, info in list(remote_players.items()):
                    if info.get('dead'):
                        continue
                    if netclient.ram_cooldowns.get(pid, 0) > 0:
                        continue
                    if pvp_system.distance_between(player.x, player.y, info['x'], info['y'], WIDTH, HEIGHT) < pvp_system.RAM_HIT_RADIUS:
                        netclient.report_hit(pid, pvp_system.RAM_DAMAGE, netclient.id)
                        netclient.ram_cooldowns[pid] = pvp_system.RAM_COOLDOWN
            for pid in list(netclient.ram_cooldowns):
                netclient.ram_cooldowns[pid] -= dt
                if netclient.ram_cooldowns[pid] <= 0:
                    del netclient.ram_cooldowns[pid]

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
                if netclient and netclient.pvp_mode:
                    max_hp = info.get('maxHp', pvp_system.PLAYER_MAX_HP)
                    if max_hp > 0:
                        hp = info.get('hp', max_hp)
                        bw, bh = 22, 3
                        bx2 = rx - bw / 2
                        by2 = ry - 26
                        pygame.draw.rect(screen, (40, 40, 40), (int(bx2), int(by2), bw, bh))
                        frac = max(0.0, min(1.0, hp / max_hp))
                        color = (max(0, int((1 - frac) * 255)), int(frac * 255), 80)
                        pygame.draw.rect(screen, color, (int(bx2), int(by2), int(bw * frac), bh))

        hud = font.render(f"Score: {score}", True, (200, 200, 200))
        screen.blit(hud, (8, 8))
        if netclient:
            hud2 = font.render("PvP ON" if netclient.pvp_mode else "PvP OFF (press V)", True, (170, 170, 220))
            screen.blit(hud2, (8, 30))
            if netclient.pvp_mode:
                hud3 = font.render(f"HP: {max(0, player.hp)}/{player.max_hp}", True, (230, 170, 170))
                screen.blit(hud3, (8, 52))

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
    parser.add_argument(
        "--log-level", default="debug",
        choices=("debug", "info", "warning", "error", "critical"),
        help="Minimum log level to emit (default: debug)",
    )
    parser.add_argument(
        "--log-forward", default=None, metavar="HOST:PORT",
        help="Instead of hosting a log listener, push all log entries to a "
             "central log server at HOST:PORT (e.g. 127.0.0.1:9000)",
    )
    args = parser.parse_args()
    set_log_level(args.log_level)
    if args.log_forward:
        fwd_host, fwd_port = parse_forward_address(args.log_forward)
        start_log_forward(fwd_host, fwd_port)
    else:
        start_log_server(port=args.log_port)
    try:
        main(args.server, args.port)
    except KeyboardInterrupt:
        log.info("Game shutting down")
        pygame.quit()
        stop_log_server()
        stop_log_forward()
        sys.exit(0)
    except Exception as e:
        log.critical(f"Fatal error: {e}")
        pygame.quit()
        stop_log_server()
        stop_log_forward()
        sys.exit(1)
