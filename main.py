# main.py
import json
import cv2
import pathlib
from pipeline.registry import create_step
import pipeline.filters
from util.io import open_input_stream
from pipeline.registry import create_step
from util.profiler import PipelineProfiler


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

    with open(config_path, "r") as f:
        config = json.load(f)

    cfg = config["config"]
    steps = load_pipeline(cfg, config["pipe_config"])
    
    stream = open_input_stream(cfg["input_root"],cfg["input_type"], cfg["input_source"], cfg.get("framerate", 0))
    
    if cfg.get("visualize", False):
        window_name = cfg.get("window_name","Window")
        cv2.namedWindow(window_name) # WINDOW_NORMAL allows resizing
        cv2.moveWindow(window_name, 0, 0)
        # cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    profiler = PipelineProfiler(window_size=30, print_interval=100,desired_framerate=cfg.get("framerate", 0))

    cv_delay = 0 if cfg["input_type"] == "image" else 1
    save_frameset = False
    while stream.is_open():
        profiler.start_frame()
        # Get next frame
        frame = stream.read()
        if frame is None:
            break
        
        # Apply all pipeline steps
        for step in steps:
            #Start step timer
            profiler.start_step(step.__class__.__name__)

            frame = step.apply(frame)
            # Will only save if "output_file" is changed from default for that step
            if cfg["input_type"] == "image" or save_frameset == True:
                step.save_output(cfg["output_root"],frame,cfg["numbered_files"])
            # End step timer
            profiler.end_step()
        save_frameset = False

        #TODO: apply viewport
        #TODO: resize final frame, implement different resize modes
        #TODO: create write final frame function, which also handles recording
        #TODO: Implement average framerate tracker/warning

        # End frame timer
        profiler.end_frame()

        if cfg.get("visualize", False):
            cv2.imshow(window_name, frame)

            key = cv2.waitKey(cv_delay) & 0xFF
            if key != 255: print(f"[{chr(key).center(3)} / {key}] pressed: ", end="")
            if key == ord("q"):
                print ("Quitting...")
                break
            elif key == ord("x"):
                print("Saving frameset...")
                save_frameset = True

        #TODO: configure step parameters during runtime (drawn ui, pop ups to set values)
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