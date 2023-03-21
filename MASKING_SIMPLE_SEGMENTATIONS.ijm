// ask user to select a folder
// we want to give this the directory with the MIP CZI files in it!!!!!
dir = getDirectory("Select A folder with MIPs (will be opened with bioformats importer)");
// get the list of files (& folders) in it


// ask user to select a folder
// we want to give this the directory with the ilastik simple segmentation files in it!!!!!
prediction_dir = getDirectory("Select A folder with ilastik simple segmentations");
// get the list of files (& folders) in it



fileList = getFileList(dir);
// prepare a folder to output the images
output_dir = dir + File.separator + "mask_combined_output" + File.separator ;
File.makeDirectory(output_dir);


//activate batch mode
setBatchMode(true);

// LOOP to process the list of files
for (i = 0; i < lengthOf(fileList); i++) {
	// define the "path" 
	// by concatenation of dir and the i element of the array fileList
	current_imagePath = dir+fileList[i];
	// check that the currentFile is not a directory
	if (!File.isDirectory(current_imagePath)){

		print(prediction_dir + "C4-" + fileList[i].substring(0, 9) + "_Simple Segmentation.tif");

		// next step is to open and select the object prediction map
		print(fileList[i].substring(0, 13));
		open(prediction_dir + "C4-" + fileList[i].substring(0,9) + "_Simple Segmentation.tif");

		run("Threshold...");
		setThreshold(1, 255);
		run("Convert to Mask");
		
		run("Analyze Particles...", "  show=Overlay clear add");

		// now to measure the p2y12 signal

		// open the image and split
		run("Bio-Formats Importer", "open=" + current_imagePath + " autoscale color_mode=Grayscale rois_import=[ROI manager] view=Hyperstack stack_order=XYCZT");
		// get some info about the image
		getDimensions(width, height, channels, slices, frames);
		// if it's a multi channel image
		if (channels > 1) run("Split Channels");
		
		ch_nbr = 1 ; 
		selectImage(ch_nbr);
		roiManager("Measure");
		
		ch_nbr = 2 ; 
		selectImage(ch_nbr);
		roiManager("Measure");

		ch_nbr = 3 ; 
		selectImage(ch_nbr);
		roiManager("Measure");
		
		ch_nbr = 4 ; 
		selectImage(ch_nbr);
		roiManager("Measure");
		
		saveAs("Measurements", output_dir +fileList[i].substring(0, 9)+"_full_output_fiji.csv");
		// make sure to close every images befores opening the next one
		run("Close All");
	}
}

saveAs("Results", output_dir+"results.csv");


setBatchMode(false);