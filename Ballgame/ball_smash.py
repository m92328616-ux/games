# Online Converter, URL: http://convert.pystage.org/conversion/Uassf-YhVuk
# ball_smash (pyStage, converted from Scratch 3)

from pystage.en import Sprite, Stage

stage = Stage()
stage.add_backdrop('backdrop1_61')
stage.create_variable('Hgap')
stage.create_variable('Hspeed')
stage.create_variable('Vgap')
stage.create_variable('Vspeed')
stage.create_variable('BlockCount')
stage.create_variable('Launches')
stage.create_variable('Score')
stage.create_variable('Fallspeed')
stage.show_variable("Score")
stage.set_monitor_position("Score", -235, 175)

# Create and initialize sprite 'ball'
ball = stage.add_a_sprite(None)
ball.set_name("Ball")
ball.set_x(-210)
ball.set_y(-110)
ball.go_to_back_layer()
ball.go_forward(1)
ball.set_size_to(80)
ball.add_costume('ball_a_15', center_x=22, center_y=22)
ball.add_costume('ball_b_13', center_x=22, center_y=22)
ball.add_costume('ball_c_13', center_x=22, center_y=22)
ball.add_costume('ball_d_13', center_x=22, center_y=22)
ball.add_costume('ball_e_13', center_x=22, center_y=22)
ball.add_sound('boing_16')
ball.add_sound('pop_74')

# Create and initialize sprite 'block'
block = stage.add_a_sprite(None)
block.set_name("Block")
block.set_x(36)
block.set_y(28)
block.go_to_back_layer()
block.go_forward(2)
block.set_size_to(50)
block.hide()
block.add_costume('costume1_342', center_x=66.5, center_y=57.5)
block.add_sound('pop_74')

# Create and initialize sprite 'arrow1'
arrow1 = stage.add_a_sprite(None)
arrow1.set_name("Arrow1")
arrow1.set_x(120)
arrow1.set_y(1)
arrow1.go_to_back_layer()
arrow1.go_forward(3)
arrow1.point_in_direction(71.4089322732197)
arrow1.add_costume('arrow1_a', center_x=28, center_y=23)
arrow1.add_costume('arrow1_b', center_x=28, center_y=23)
arrow1.add_costume('arrow1_c', center_x=23, center_y=28)
arrow1.add_costume('arrow1_d', center_x=23, center_y=28)
arrow1.add_sound('pop_74')

# Scratch Blocks for 'ball'

def when_program_starts_1(self):
    self.set_variable("Score", 0)
    self.set_variable("Launches", 0)
    "NO TRANSLATION: procedures_call"

ball.when_program_starts(when_program_starts_1)

def when_i_receive_message_2(self):
    self.reset_timer()
    self.change_variable_by("Launches", -1.0)
    self.set_variable("Hgap", (self.mouse_x() - self.x_position()))
    self.set_variable("Vgap", (self.mouse_y() - self.y_position()))
    self.set_variable("Hgap", (self.get_variable("Hgap") / 30.0))
    self.set_variable("Vgap", (self.get_variable("Vgap") / 30.0))
    while not ((self.timer() > 5) or self.touching_edge()):
        "NO TRANSLATION: procedures_call"

    "NO TRANSLATION: procedures_call"

ball.when_i_receive_message("fire", when_i_receive_message_2)

def when_i_receive_message_3(self):
    self.say("".join(["You Scored:", self.get_variable("Score")]))
    self.wait(3.0)
    self.stop_all()

ball.when_i_receive_message("Completed Game", when_i_receive_message_3)

# Scratch Blocks for 'block'

def when_program_starts_4(self):
    self.set_size_to(50.0)
    self.show()
    "NO TRANSLATION: procedures_call"

block.when_program_starts(when_program_starts_4)

def when_i_start_as_a_clone_5(self):
    self.set_variable("Fallspeed", 0)
    self.go_to_x_y(self.pick_random(180.0, 200.0), (-154.0 + (self.get_variable("BlockCount") * 35.0)))
    while not (self.get_variable("BlockCount") == 0):
        if self.touching(ball):
            self.hide()
            self.change_variable_by("Launches", self.get_variable("Launches"))
            self.change_variable_by("BlockCount", -1.0)
            self.play_sound_until_done("pop_74")
            self.set_variable("Hspeed", (-0.8 * self.get_variable("Hspeed")))

        if not (self.touching_color((0, 208, 66))):
            self.change_variable_by("Fallspeed", -0.1)
            self.change_y_by(self.get_variable("Fallspeed"))

    self.broadcast("Completed Game")

block.when_i_start_as_a_clone(when_i_start_as_a_clone_5)

# Scratch Blocks for 'arrow1'

def when_program_starts_6(self):
    self.set_pen_color((247, 208, 36))
    self.set_pen_size_to(15.0)
    self.show()
    while True:
        self.erase_all()
        self.go_to_x_y(self.x_position_of(ball), self.y_position_of(ball))
        self.go_to_mouse_pointer()
        self.point_towards_sprite(ball)
        self.turn_right(180.0)

arrow1.when_program_starts(when_program_starts_6)

def when_this_sprite_clicked_7(self):
    self.broadcast("fire")
    self.hide()
    self.pen_up()

arrow1.when_this_sprite_clicked(when_this_sprite_clicked_7)

def when_i_receive_message_8(self):
    self.show()
    self.pen_down()

arrow1.when_i_receive_message("Get Ready", when_i_receive_message_8)

stage.play()
