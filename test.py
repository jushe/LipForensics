import argparse

import torch
from torch.utils.data import DataLoader
from torchvision.transforms import Compose, CenterCrop
from data.transforms import NormalizeVideo, ToTensorVideo
from models.spatiotemporal_net import get_model
from tqdm import tqdm
import cv2
import numpy as np
from PIL import Image

def load_video_frames(video_path):
    # Open the video file
    cap = cv2.VideoCapture(video_path)

    frames = []
    while cap.isOpened():
        # Read a frame from the video
        ret, frame = cap.read()

        # Check if the frame was successfully read
        if not ret:
            break

        # Convert the frame to RGB format
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Append the frame to the list
        frames.append(frame_rgb)

    # Release the video capture object
    cap.release()

    # Convert the list of frames to a NumPy array
    frames_array = np.stack(frames)

    # Transpose to match the desired shape [T, H, W, C]
    frames_array = np.transpose(frames_array, (0, 3, 1, 2))
    # frames_array = torch.from_numpy(frames_array)
    # Convert NumPy array to PyTorch tensor
    frames_tensor = torch.from_numpy(frames_array).unsqueeze(-1)

    return frames_tensor

# Example usage:
# video_path = "path/to/your/video.mp4"
# video_frames = load_video_frames(video_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate LipForensics model on a single video")
    parser.add_argument("--video_path", help="Path to the input video file", type=str, required=True)
    parser.add_argument("--weights_forgery_path", help="Path to pretrained weights for forgery detection",
                        type=str, default="./models/weights/lipforensics_ff.pth")
    parser.add_argument("--frames_per_clip", default=25, type=int)
    parser.add_argument("--device", help="Device to put tensors on", type=str, default="cuda:0")

    args = parser.parse_args()
    return args

def evaluate_video(model, video_frames, args):
    model.eval()
    print(video_frames.shape)
    # Define the transformation for each video frame
    transform = Compose([ToTensorVideo(), CenterCrop((88, 88)), NormalizeVideo((0.421,), (0.165,))])

    # Create a DataLoader to handle batching and transformation
    data_loader = DataLoader(video_frames, batch_size=32, shuffle=False)

    video_to_logits = []
    with torch.no_grad():
        for batch_frames in tqdm(data_loader):
            # print(batch_frames.shape)
            # Apply the transformation to the batch of frames
            batch_frames_transformed = torch.stack([transform(frame) for frame in batch_frames])
            batch_frames = batch_frames_transformed
            batch_frames = batch_frames.to(args.device)

            # Forward
            logits = model(batch_frames, lengths=[args.frames_per_clip] * batch_frames.shape[0])
            video_to_logits.append(logits)

    # Concatenate logits from all batches
    video_logits = torch.cat(video_to_logits, dim=0)

    # Calculate the final score (e.g., average or max)
    final_score = torch.sigmoid(video_logits).mean().item()

    return final_score

def main():
    args = parse_args()

    # Load LipForensics model
    model = get_model(weights_forgery_path=args.weights_forgery_path)

    # Load video frames
    video_frames = load_video_frames(args.video_path)

    # Evaluate video
    score = evaluate_video(model, video_frames, args)
    print(f"Forgery score for {args.video_path}: {score}")

if __name__ == "__main__":
    main()
