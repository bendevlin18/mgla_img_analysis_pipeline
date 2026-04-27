// === Parameters ===
Dialog.create("MGLA pipeline parameters");
Dialog.addNumber("Ilastik segmentation channel (1-based)", 4);
Dialog.addNumber("Filename key length (chars)", 9);
Dialog.addString("Ilastik filename suffix", "_Simple Segmentation.tif");
Dialog.addString("Channel labels (comma-separated, optional)", "");
Dialog.show();

segChannel        = Dialog.getNumber();
keyLen            = Dialog.getNumber();
ilastikSuffix     = Dialog.getString();
channelLabelsRaw  = Dialog.getString();

ilastikPrefix = "C" + segChannel + "-";
useLabels     = (lengthOf(channelLabelsRaw) > 0);
channelLabels = newArray(0);
if (useLabels) channelLabels = split(channelLabelsRaw, ",");


// === Directories ===
dir            = getDirectory("Select A folder with MIPs (will be opened with bioformats importer)");
prediction_dir = getDirectory("Select A folder with ilastik simple segmentations");

fileList   = getFileList(dir);
output_dir = dir + File.separator + "mask_combined_output" + File.separator;
File.makeDirectory(output_dir);


setBatchMode(true);

for (i = 0; i < lengthOf(fileList); i++) {
	current_imagePath = dir + fileList[i];
	if (File.isDirectory(current_imagePath)) continue;
	if (lengthOf(fileList[i]) < keyLen) {
		print("Skipping " + fileList[i] + ": shorter than key length " + keyLen);
		continue;
	}

	key      = fileList[i].substring(0, keyLen);
	seg_path = prediction_dir + ilastikPrefix + key + ilastikSuffix;

	if (!File.exists(seg_path)) {
		print("Skipping " + fileList[i] + ": segmentation not found at " + seg_path);
		continue;
	}

	// open ilastik segmentation, threshold, build ROIs
	open(seg_path);
	run("Threshold...");
	setThreshold(1, 255);
	run("Convert to Mask");
	run("Analyze Particles...", "  show=Overlay clear add");

	// open the multi-channel image and split
	run("Bio-Formats Importer", "open=" + current_imagePath + " autoscale color_mode=Grayscale rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT");
	getDimensions(width, height, channels, slices, frames);
	if (channels > 1) run("Split Channels");

	// measure ROIs against every channel, tag each row with its channel name
	for (ch = 1; ch <= channels; ch++) {
		if (useLabels && ch <= lengthOf(channelLabels)) {
			label = channelLabels[ch - 1];
		} else {
			label = "ch" + ch;
		}

		nBefore = nResults;
		selectImage(ch);
		roiManager("Measure");
		for (r = nBefore; r < nResults; r++) {
			setResult("Channel", r, label);
		}
	}
	updateResults();

	saveAs("Measurements", output_dir + key + "_full_output_fiji.csv");
	run("Close All");
}

saveAs("Results", output_dir + "results.csv");

setBatchMode(false);
