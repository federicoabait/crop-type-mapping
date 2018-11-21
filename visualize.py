"""
import random

File for visualizing model performance.

"""

import numpy as np
import matplotlib.pyplot as plt
import visdom

import preprocess
import util
from constants import * 

def setup_visdom(env_name, model_name):
    # TODO: Add args to visdom envs default name
    if not env_name:
        env_name = "{}".format(model_name)
    else:
        env_name = env_name
    return visdom.Visdom(port=8097, env=env_name)

def visdom_plot_metric(metric_name, split, title, x_label, y_label, vis_data, vis):
    """
    Args: 
      metric_name - "loss", "acc", "f1"
    """
    vis.line(Y=np.array(vis_data['{}_{}'.format(split, metric_name)]),
             X=np.array(range(len(vis_data['{}_{}'.format(split, metric_name)]))),
             win=title,
             opts={'legend': ['{}_{}'.format(split, metric_name)],
                   'markers': False, 
                   'title': title,
                   'xlabel': x_label,
                   'ylabel': y_label})

def visdom_plot_many_metrics(metric_name, split, title, x_label, y_label, legend_lbls, vis_data, vis):
    """
    Args: 
      metric_name - "loss", "acc", "f1"
    """
    #Y = np.vstack(vis_data['{}_{}'.format(split, metric_name)])
    vis.line(Y=np.vstack(vis_data['{}_{}'.format(split, metric_name)]),
             X=np.array(range(len(vis_data['{}_{}'.format(split, metric_name)]))),
             win=title,
             opts={'legend': legend_lbls,
                   'markers': False, 
                   'title': title,
                   'xlabel': x_label,
                   'ylabel': y_label})
    
def visdom_plot_images(vis, imgs, win):
    """
    Plot image panel in visdom
    Args: 
      imgs - (array) array of images [batch x channels x rows x cols]
      win - (str) serves as both window name and title name
    """
    vis.images(imgs, nrow=NROW, win=win, 
               opts={'title': win})

def record_batch(inputs, clouds, targets, preds, num_classes, split, vis_data, vis, include_doy, use_s1, use_s2, model_name, time_slice):
    """ Record values and images for batch in visdom
    """
    # Create and show mask for labeled areas
    label_mask = np.sum(targets.numpy(), axis=1)
    label_mask = np.expand_dims(label_mask, axis=1)
    visdom_plot_images(vis, label_mask, 'Label Masks')

    # Show best inputs judging from cloud masks
    if torch.sum(clouds) != 0 and len(clouds.shape) > 1: 
        best = np.argmax(np.mean(np.mean(np.squeeze(clouds.numpy()), axis=1), axis=1), axis=1)
    else:
        best = np.random.randint(0, high=MIN_TIMESTAMPS, size=(inputs.shape[0],))

    # Get bands of interest (boi) to show best rgb version of s2 or vv, vh, vv version of s1
    boi = []
    add_doy = 0
    if use_s2 and use_s1:
        if include_doy: 
            add_doy = 1
        if model_name in ['fcn_crnn', 'bidir_clstm']:
            for idx, b in enumerate(best):
                boi.append(inputs[idx, b, 2+add_doy:5+add_doy, :, :].unsqueeze(0))
            boi = torch.cat(boi, dim=0)
        elif model_name in ['fcn', 'unet'] and time_slice is not None:
            boi = inputs[:, 2+add_doy:5+add_doy, :, :]
        elif model_name in ['unet'] and time_slice is None:
            inputs = inputs.view(inputs.shape[0], MIN_TIMESTAMPS, -1, inputs.shape[2], inputs.shape[3])  
            for idx, b in enumerate(best):
                boi.append(inputs[idx, b, 2+add_doy:5+add_doy, :, :].unsqueeze(0))
            boi = torch.cat(boi, dim=0)
    elif use_s1:
        if model_name in ['fcn_crnn', 'bidir_clstm']:
            for idx, b in enumerate(best):
                boi.append(torch.cat((inputs[idx, b, 0:2, :, :], inputs[idx, b, 0, :, :].unsqueeze(0)), dim=0).unsqueeze(0))
            boi = torch.cat(boi, dim=0)
        elif model_name in ['fcn', 'unet'] and time_slice is not None:
            boi = torch.cat((inputs[:, 0:2, :, :], inputs[:, 0, :, :].unsqueeze(1)), dim=1)
        elif model_name in ['unet'] and time_slice is None:
            inputs = inputs.view(inputs.shape[0], MIN_TIMESTAMPS, -1, inputs.shape[2], inputs.shape[3])  
            for idx, b in enumerate(best):
                boi.append(torch.cat((inputs[idx, b, 0:2, :, :], inputs[idx, b, 0, :, :].unsqueeze(0)), dim=0).unsqueeze(0))
            boi = torch.cat(boi, dim=0)
    elif use_s2:
        if model_name in ['fcn_crnn', 'bidir_clstm']:
            for idx, b in enumerate(best):
                boi.append(inputs[idx, b, 0:3, :, :].unsqueeze(0))
            boi = torch.cat(boi, dim=0)
        elif model_name in ['fcn', 'unet'] and time_slice is not None:
            boi = inputs[:, 0:3, :, :]
        elif model_name in ['unet'] and time_slice is None:
            inputs = inputs.view(inputs.shape[0], MIN_TIMESTAMPS, -1, inputs.shape[2], inputs.shape[3]) 
            for idx, b in enumerate(best):
                boi.append(inputs[idx, b, 0:3, :, :].unsqueeze(0))
            boi = torch.cat(boi, dim=0)
    
    # Clip and show input bands of interest
    boi = clip_boi(boi)
    visdom_plot_images(vis, boi, 'Input Images') 

    # Show targets (labels)
    disp_targets = np.concatenate((np.zeros_like(label_mask), targets.numpy()), axis=1)
    disp_targets = np.argmax(disp_targets, axis=1)
    disp_targets = np.expand_dims(disp_targets, axis=1)
    disp_targets = visualize_rgb(disp_targets, num_classes)
    visdom_plot_images(vis, disp_targets, 'Target Images')

    # Show predictions, masked with label mask
    disp_preds = np.argmax(preds.detach().cpu().numpy(), axis=1) + 1
    disp_preds = np.expand_dims(disp_preds, axis=1)
    disp_preds = visualize_rgb(disp_preds, num_classes)
    disp_preds_w_mask = disp_preds * label_mask

    visdom_plot_images(vis, disp_preds, 'Predicted Images')
    visdom_plot_images(vis, disp_preds_w_mask, 'Predicted Images with Label Mask')

    # Show gradnorm per batch
    if split == 'train':
        visdom_plot_metric('gradnorm', split, 'Grad Norm', 'Batch', 'Norm', vis_data, vis)

def clip_boi(boi):
    """ Clip bands of interest outside of 2*std per imagei sample
    """
    for sample in range(boi.shape[0]):
        sample_mean = torch.mean(boi[sample, :, :, :])
        sample_std = torch.std(boi[sample, :, :, :])
        min_clip = sample_mean - 2*sample_std
        max_clip = sample_mean + 2*sample_std

        boi[sample, :, :, :][boi[sample, :, :, :] < min_clip] = min_clip
        boi[sample, :, :, :][boi[sample, :, :, :] > max_clip] = max_clip
    
        boi[sample, :, :, :] = (boi[sample, :, :, :] - min_clip)/(max_clip - min_clip)
    return boi

def record_epoch(all_metrics, split, vis_data, vis, epoch_num):
    """ Record values for epoch in visdom
    """
    #f1s = [x for x in all_metrics[f'{split}_f1'] if x is not None]
    #if f1s is not None: f1_epoch = np.mean(f1s)
    if all_metrics[f'{split}_loss'] is not None: loss_epoch = all_metrics[f'{split}_loss'] / all_metrics[f'{split}_pix']
    if all_metrics[f'{split}_acc'] is not None: acc_epoch = all_metrics[f'{split}_acc'] / all_metrics[f'{split}_pix']

    vis_data[f'{split}_loss'].append(loss_epoch)
    vis_data[f'{split}_acc'].append(acc_epoch)
    vis_data[f'{split}_f1'].append(metrics.get_f1score(all_metrics[f'{split}_cm'], avg=True))
    vis_data[f'{split}_classf1'].append(metrics.get_f1score(all_metrics[f'{split}_cm'], avg=False))

    visdom_plot_metric('loss', split, f'{split} Loss', 'Epoch', 'Loss', vis_data, vis)
    visdom_plot_metric('acc', split, f'{split} Accuracy', 'Epoch', 'Accuracy', vis_data, vis)
    visdom_plot_metric('f1', split, f'{split} f1-score', 'Epoch', 'f1-score', vis_data, vis)
    visdom_plot_many_metrics('classf1', split, f'{split} per class f1-score', 'Epoch', CM_CLASSES, 'per class f1-score', vis_data, vis)
               
    fig = util.plot_confusion_matrix(all_metrics[f'{split}_cm'], CM_CLASSES,
                                     normalize=False,
                                     title='{} confusion matrix, epoch {}'.format(split, epoch_num),
                                     cmap=plt.cm.Blues)

    vis.matplot(fig, win=f'{split} CM')

def visualize_rgb(argmax_array, num_classes, class_colors=None): 
    mask = []
    rgb_output = np.zeros((argmax_array.shape[0], 3, argmax_array.shape[2], argmax_array.shape[3]))

    if class_colors == None:
        rgbs = [ [255, 0, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255] ]
    
    assert len(rgbs) == num_classes

    for cur_class in range(0, num_classes):
        tmp = np.asarray([argmax_array == cur_class+1])[0]

        mask_cat = np.concatenate((tmp, tmp, tmp), axis=1)

        class_vals = np.concatenate((np.ones_like(tmp)*rgbs[cur_class][0],
                                     np.ones_like(tmp)*rgbs[cur_class][1],
                                     np.ones_like(tmp)*rgbs[cur_class][2]), axis=1) 

        rgb_output += (mask_cat * class_vals)
        
    return rgb_output


def visualize_model_preds(model, grid_name, save=False):
    """ Outputs a visualization of model predictions for one grid.

    Args:
        model - (ML model) model to be evaluated
        grid_name - (string) name of the grid to evaluate
    """
    # assuming there is some way to store the model's name in the model itself
    # assuming these functions exists somewhere in preprocess
    
    # TODO: This function as a whole is a WIP -- was abandoned to
    #  get visdom working instead ... 

    label = preprocess.retrieve_label(grid_name, country) # get the mask given a grid's name (ex: "004232")
    best_grid = preprocess.retrieve_best_s2_grid(grid_name, country) # get the actual grid data given a grid's name
    
    grid = preprocess.preprocess_grid(grid, model.name) # preprocess the grid in a model specific way

    preds = model.predict(grid) # get model predictions

    # formats preds into a 64x64 grid and creates a visualization of the predicted values
    # masking everything that's not labeled
    visualize_preds(preds, mask)

    # save if flag set

