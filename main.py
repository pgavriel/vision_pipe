# main.py
import json
import cv2
import pathlib
from os.path import join, dirname
import os
from pipeline.registry import create_step
import pipeline.filters
import pipeline.layer
from util.io import open_input_stream, get_unique_output_path, export_config
from pipeline.registry import create_step
from util.profiler import PipelineProfiler
from util.message_handler import MessageManager
from tools.viewport_tool import Viewport, ViewportAnimator
from tools.obs_controller import OBSController


def load_pipeline(global_config, pipe_config, verbose=True):
    print(f"=====\nGlobal Config:")
    for k in global_config:
        print(f"[{k.center(20)}]: {global_config[k]}")
    if verbose: print("=====\nLoading Pipeline...")
    if pipe_config.get("load_from_file"):
        with open(pipe_config["pipe"], "r") as f:
            steps = json.load(f)
    else:
        steps = pipe_config["pipe"]
    steps = [create_step(step["name"], global_config, step.get("params", {})) for step in steps]
    if verbose:
        for step in steps: 
            print(step)
            step.verbose = True
        print("=====\n")
    return steps

def run_pipeline(config_path):
    import json
    import cv2
    from util.io import open_input_stream
    from pipeline.registry import create_step

    # Load Config File
    with open(config_path, "r") as f:
        config = json.load(f)
    cfg = config["config"]
    steps = load_pipeline(cfg, config["pipe_config"])
    selected_step = 0
    selected_param = 0
    current_param_multiplier = 0
    param_multipliers = [1,5,10,100]

    # Open Input Stream
    stream = open_input_stream(cfg["input_root"],cfg["input_type"], cfg["input_source"], cfg.get("framerate", 0))
    if cfg.get("visualize", False):
        window_name = cfg.get("window_name","Window")
        cv2.namedWindow(window_name) # WINDOW_NORMAL allows resizing
        cv2.moveWindow(window_name, 0, 0)
        # if cfg.get("fullscreen",False):
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    # Setup frame/process timer
    profiler = PipelineProfiler(window_size=30, print_interval=100,desired_framerate=cfg.get("framerate", 0))

    # Setup text message handler
    msg = MessageManager()
    msg.add_message("status", "Startup successful...", duration=30, color=(0,255,0), size=1, position=(100,100))

    # Setup OBS Websocket controller (for recording video)
    obs = OBSController(password="visionpipe")

    # Get initial frame
    while stream.is_open():
        frame = stream.read()
        h,w,_ = frame.shape
        print(f"Stream Size: {w}x{h}")
        break
    # Setup Viewport
    vp_step = 10
    vp_mode = "relative"
    vp = Viewport(frame,w//2,h//2,w,h)
    vp.debug = False
    vp.update()
    vp_animator = ViewportAnimator()
    vp_animator.update()

    cv_delay = 0 if cfg["input_type"] == "image" else 1
    save_frameset, save_screenshot = (False, False)
    while stream.is_open():
        profiler.start_frame()
        # Get next frame
        frame = stream.read()
        if frame is None:
            break
        
        vp_animator.update()
        if vp_animator.playing:
            vp.set_state(vp_animator.current_state)
        vp.image = frame
        vp.update()
        frame = vp.view

        # Apply all pipeline steps
        for step in steps:
            if not step.params.get("enabled",True):
                continue
            #Start step timer
            profiler.start_step(step.__class__.__name__)

            frame = step.apply(frame)
            # Will only save if "output_file" is changed from default for that step
            if cfg["input_type"] == "image" or save_frameset == True:
                step.save_output(cfg["output_root"],frame,cfg["numbered_files"])
            # End step timer
            profiler.end_step()
        save_frameset = False
        

        #TODO: create write final frame function, which also handles recording
        if save_screenshot:
            # write numbered frame
            out_path = get_unique_output_path(join(cfg["output_root"],f"screenshots/{cfg['screenshot_label']}.png"))
            os.makedirs(dirname(out_path), exist_ok=True)
            ss_frame = frame.copy()
            if cfg["screenshot_rotations"] != 0:
                rotate = cv2.ROTATE_90_COUNTERCLOCKWISE
                if cfg["screenshot_rotations"]%4 == 1: rotate = cv2.ROTATE_90_CLOCKWISE
                elif cfg["screenshot_rotations"]%4 == 2: rotate = cv2.ROTATE_180
                print(f"SS: {cfg['screenshot_rotations']} -- {rotate}")
                ss_frame = cv2.rotate(ss_frame,rotate)
            cv2.imwrite(out_path,ss_frame)
            save_screenshot = False


        #TODO: resize final frame, implement different resize modes
        #TODO: Implement average framerate tracker/warning

        # End frame timer
        profiler.end_frame()

        if cfg.get("visualize", False):
            # Draw GUI messages
            msg.draw(frame)
            # Show frame
            cv2.imshow(window_name, frame)

            # Handle GUI Controls
            key = cv2.waitKey(cv_delay) & 0xFF
            if key != 255: print(f"[{chr(key).center(3)} / {key}] pressed: ", end="")
            # ==== QUIT ====
            if key == ord("q"):
                print ("Quitting...")
                break
            # ==== SAVE OUTPUTS ====
            elif key == ord("x"): # Save frameset
                msg.add_message("status","Saving frameset...")
                save_frameset = True
            elif key == ord("z"): # Save screenshot
                msg.add_message("status","Saving screenshot...")
                save_screenshot = True   
            elif key == ord("m"): # Start/Stop Recording Video
                obs.toggle_recording()
                # print(obs.get_recording_status())
            elif key == ord("n"): # Save current config
                pipe_cfg = {"load_from_file": False, "pipe":[step.to_dict() for step in steps]}
                out_cfg = {"config":cfg,"pipe_config":pipe_cfg}
                export_config(out_cfg,config_path)
            # ==== CONFIGURE PIPELINE ====
            elif key == ord("1"): # Select previous step
                if len(steps) > 0: 
                    # Select previous step
                    selected_step = (selected_step - 1) % len(steps)
                    step_name = steps[selected_step].__class__.__name__
                    msg.add_message("status",f"[Step {selected_step+1}/{len(steps)}] {step_name}")
                    # Select initial parameter
                    selected_param = 0 if len(steps[selected_step].params.keys()) > 0 else None
                    if selected_param is not None:
                        param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                        msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
                    else:
                        msg.add_message("config",f"[0 Params]",position=(10,100))
            elif key == ord("2"): # Select next step
                if len(steps) > 0: 
                    # Select next step
                    selected_step = (selected_step + 1) % len(steps)
                    step_name = steps[selected_step].__class__.__name__
                    msg.add_message("status",f"[Step {selected_step+1}/{len(steps)}] {step_name}")
                    # Select initial parameter
                    selected_param = 0 if len(steps[selected_step].params.keys()) > 0 else None
                    if selected_param is not None:
                        param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                        msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
                    else:
                        msg.add_message("config",f"[0 Params]",position=(10,100))
            elif key == ord("3"): # Select previous parameter
                total_params = len(steps[selected_step].params.keys())
                if total_params > 0:
                    selected_param = (selected_param - 1) % total_params
                    param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                    msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
                else:
                    msg.add_message("config",f"[0 Params]",position=(10,100))
            elif key == ord("4"): # Select next parameter
                total_params = len(steps[selected_step].params.keys())
                if total_params > 0:
                    selected_param = (selected_param + 1) % total_params
                    param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                    msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
                else:
                    msg.add_message("config",f"[0 Params]",position=(10,100))
            elif key == ord("5"): # Decrease selected parameter
                if selected_param is not None:
                    param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                    steps[selected_step].edit_parameter(param_name,"down",param_multipliers[current_param_multiplier])
                    msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
            elif key == ord("6"): # Increase selected parameter
                if selected_param is not None:
                    param_name, param_val = list(steps[selected_step].params.items())[selected_param]
                    steps[selected_step].edit_parameter(param_name,"up",param_multipliers[current_param_multiplier])
                    msg.add_message("config",f"[Param {selected_param+1}/{len(steps[selected_step].params.keys())}] {param_name} = {param_val}",position=(10,100))
            elif key == ord("7"): # Cycle through param multipliers
                current_param_multiplier = (current_param_multiplier + 1) % len(param_multipliers)
                msg.add_message("config",f"[Param Multiplier]: {param_multipliers[current_param_multiplier]}",position=(10,100))
            elif key == ord("8"): # Move step BACKWARD in list
                if selected_step > 0:
                    temp = steps[selected_step-1]
                    steps[selected_step-1] = steps[selected_step]
                    steps[selected_step] = temp
                    selected_step = selected_step - 1
                    step_name = steps[selected_step].__class__.__name__
                    msg.add_message("status",f"[Step {selected_step+1}/{len(steps)}] {step_name}")
            elif key == ord("9"): # Move step FORWARD in list
                if selected_step < len(steps)-1:
                    temp = steps[selected_step+1]
                    steps[selected_step+1] = steps[selected_step]
                    steps[selected_step] = temp
                    selected_step = selected_step + 1
                    step_name = steps[selected_step].__class__.__name__
                    msg.add_message("status",f"[Step {selected_step+1}/{len(steps)}] {step_name}")
            elif key == ord("`"): # Toggle step "enabled" param
                if len(steps) > 0:
                    step_name = steps[selected_step].__class__.__name__
                    steps[selected_step].params["enabled"] = not steps[selected_step].params.get("enabled",True)
                    step_enabled = steps[selected_step].params["enabled"]
                    msg.add_message("config",f"{step_name} enabled: {step_enabled}",position=(50,100))
            # ==== VIEWPORT CONTROLS ====
            elif key == ord("w"): # Viewport Up
                vp.move("up",param_multipliers[current_param_multiplier],vp_mode)
                print("[VP] Up")
            elif key == ord("a"): # Viewport Left
                vp.move("left",param_multipliers[current_param_multiplier],vp_mode)
                print("[VP] Left")
            elif key == ord("s"): # Viewport Down
                vp.move("down",param_multipliers[current_param_multiplier],vp_mode)
                print("[VP] Down")
            elif key == ord("d"): # Viewport Right
                vp.move("right",param_multipliers[current_param_multiplier],vp_mode)
                print("[VP] Right")
            elif key == ord("r"): # Viewport Zoom In
                vp.h = int(max(vp.h * 0.9,10))
                vp.w = int(max(vp.w * 0.9,10))
                print("[VP] Zoom In: ",vp.w,vp.h)
            elif key == ord("e"): # Viewport Zoom Out
                vp.h = int(min(vp.h * 1.1,h))
                vp.w = int(min(vp.w * 1.1,w))
                print("[VP] Zoom Out: ",vp.w,vp.h)
            elif key == ord("f"): # Viewport Rotate Left
                vp.a = (vp.a + 15) % 360
                print("[VP] Rotate Left: ",vp.a)
            elif key == ord("c"): # Viewport Rotate Right
                vp.a = (vp.a - 15) % 360
                print("[VP] Rotate Right: ",vp.a)
            elif key == ord('t'): # Viewport Reset
                vp.reset()
            elif key == ord('o'): # Viewport Animator - Add state
                vp_animator.add_state(vp.get_state(),steps=75)
            elif key == ord('p'): # Viewport Animator - Play/Pause
                vp_animator.playpause()
            elif key == ord('l'):# Viewport Animator - Reset
                vp_animator.reset()
                print("7. Animator reset")


        #TODO: export config file

    stream.release()
    cv2.destroyAllWindows()
    print("\nProgram finished.\n")

if __name__ == "__main__":
    root_directory = pathlib.Path(__file__).parent.resolve()
    config_file = root_directory / "configs" / "dev_live_config_new.json"
    if config_file.resolve().exists():
        print(f"=====\nRunning Config: {config_file}")
        run_pipeline(config_file)
    else:
        print(f"Config path ( {config_file} ) not found")