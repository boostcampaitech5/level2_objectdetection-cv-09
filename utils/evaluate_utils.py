import time
import torch
from utils.train_utils import MetricLogger
from utils.mAP import mAPLogger


@torch.no_grad()
def evaluate(model, data_loader, device, mAP_list=None):
    n_threads = torch.get_num_threads()
    torch.set_num_threads(1)
    cpu_device = torch.device("cpu")
    model.eval()
    metric_logger = MetricLogger(delimiter="  ")
    map_logeer = mAPLogger(iou_threshold=0.5, num_classes = 10)
    header = "Test: "

    for image, targets in metric_logger.log_every(data_loader, 100, header):
        image = list(img.to(device) for img in image)

        if device != torch.device("cpu"):
            torch.cuda.synchronize(device)

        model_time = time.time()
        outputs = model(image)
        
        outputs = [{k: v.to(cpu_device) for k, v in t.items()} for t in outputs]
        model_time = time.time() - model_time

        pred_boxes = []
        true_boxes = []
        for target, output in zip(targets, outputs):
            img_id = target['image_id'].item()
            # output : {"boxes": [], "labels": [], "scores": [] }
            # target : {"boxes": [], "labels": [], "image_id": [], "area": [], "iscrowd": []}

            for i in range(len(target['labels'])):
                true_boxes.append([
                    img_id, 
                    target['labels'][i], 
                    target['area'][i], 
                    target['boxes'][i][0], 
                    target['boxes'][i][1], 
                    target['boxes'][i][2], 
                    target['boxes'][i][3]] )
            for i in range(len(output['labels'])):
                pred_boxes.append([
                    img_id, 
                    output['labels'][i], 
                    output['scores'][i], 
                    output['boxes'][i][0], 
                    output['boxes'][i][1], 
                    output['boxes'][i][2], 
                    output['boxes'][i][3]] )
        evaluator_time = time.time()
        map_logeer.update(pred_boxes,true_boxes)
        evaluator_time = time.time() - evaluator_time

        metric_logger.update(model_time=model_time, evaluator_time=evaluator_time)

    # gather the stats from all processes
    metric_logger.synchronize_between_processes()
    
    print("Averaged stats:", metric_logger)
    torch.set_num_threads(n_threads)
    if isinstance(mAP_list, list):
        mAP_list.append(map_logeer.get_mAP())

    return map_logeer.get_ap_list(), map_logeer.get_mAP()

