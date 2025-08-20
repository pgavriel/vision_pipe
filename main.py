# main.py
import json
import cv2
import pathlib
from os.path import join, dirname
import os
from pipeline.registry import create_step
import pipeline.filters
from util.io import open_input_stream, get_unique_output_path
from pipeline.registry import create_step
from util.profiler import PipelineProfiler
from util.message_handler import MessageManager


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


    cv_delay = 0 if cfg["input_type"] == "image" else 1
    save_frameset, save_screenshot = (False, False)
    while stream.is_open():
        profiler.start_frame()
        # Get next frame
        frame = stream.read()
        if frame is None:
            break
        
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
            cv2.imwrite(out_path,frame)
            save_screenshot = False


        #TODO: apply viewport
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
            if key == ord("q"):
                print ("Quitting...")
                break
            elif key == ord("x"): # Save frameset
                msg.add_message("status","Saving frameset...")
                save_frameset = True
            elif key == ord("s"): # Save screenshot
                msg.add_message("status","Saving screenshot...")
                save_screenshot = True    
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
            elif key == ord("7"):
                current_param_multiplier = (current_param_multiplier + 1) % len(param_multipliers)
                msg.add_message("config",f"[Param Multiplier]: {param_multipliers[current_param_multiplier]}",position=(10,100))
            elif key == ord("`"): # Toggle step "enabled" param
                if len(steps) > 0:
                    step_name = steps[selected_step].__class__.__name__
                    steps[selected_step].params["enabled"] = not steps[selected_step].params.get("enabled",True)
                    step_enabled = steps[selected_step].params["enabled"]
                    msg.add_message("config",f"{step_name} enabled: {step_enabled}",position=(50,100))

        #TODO: export config file

    stream.release()
    cv2.destroyAllWindows()
    print("\nProgram finished.\n")

if __name__ == "__main__":
    root_directory = pathlib.Path(__file__).parent.resolve()
    config_file = root_directory / "configs" / "dev_live_config.json"
    if config_file.resolve().exists():
        print(f"=====\nRunning Config: {config_file}")
        run_pipeline(config_file)
    else:
        print(f"Config path ( {config_file} ) not found")