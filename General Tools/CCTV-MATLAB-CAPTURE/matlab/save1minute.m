% SAMPLE_AVERAGE uses FrameGrabM to grab a series of frames and averages
% them together to reduce the amount of noise that may appear in the image.
% This is especially useful in low-light situations.  This also shows a
% technique for preallocation of memory to ensure that consecutive frames
% are captured without gaps in time.
%
% Version 0.8 - 06 March 2012
%modified by Nathan Killian 121103

%todo: have receive a ttl pulse to start capture and save to a .mat file
%and/or .wmv file
% 640 x 480 at 29.97 fps is format 1, all are 29.97, see formatInfos
% all are RGB24 bit
% format 2 is 160x120
% could crop out a 500 pixel region and send into plexon as a 1 kHz signal
% -> 1 fps
% anyway to reduce image size even more? taking up too much memory
% can only do about 20 seconds at 10 fps
% correct for the gained frames when doing long time segments (i.e. 30
% instead of 29.97 is used)

clar
saveMAT = 0;saveWMV = 1;
filePrefix = ['XX' datestr(now,'yymmdd') ];
fileDir = 'C:\';
seconds = 3;%can save up to 5 minutes, 300 seconds, with current settings
framesPerSec = 30;
newFramesPerSec = 10;% option to reduce the FPS to save memory
skip = framesPerSec/newFramesPerSec;

% FRAMECONSEC is the number of consecutive frames to grab in each cycle:
FRAMECONSECorig = framesPerSec * seconds;
if newFramesPerSec < framesPerSec
    FRAMECONSEC = round(FRAMECONSECorig*newFramesPerSec/framesPerSec);
end

% MYDEVICE is the capture device index that I want to use:
MYDEVICE = 1;
% MYFORMAT is the format index that I want to use for MYDEVICE:
MYFORMAT = 2;


% Initialize the capture framework:
fprintf('Initializing...\n');
fgrabm_init

% You can set the desired capture device and framework here:
fgrabm_setdefault(MYDEVICE);
fgrabm_setformat(MYFORMAT);

% Get the format information so we can preallocate memory:
fprintf('Allocating buffer...');
formatInfos = fgrabm_formats;
formatInfo = formatInfos(MYFORMAT);
capArray = zeros([formatInfo.height formatInfo.width 3 FRAMECONSEC], ...
    'uint8');
trashArray = zeros([formatInfo.height formatInfo.width 3 1],'uint8');
% We'll grab in the native format and do calculation later to avoid losing
% frames.
fprintf('Starting continuous capture...\n');
fgrabm_start;

% Wait for the device to warm up:
fprintf('Waiting for the capture device to warm up...\n');
pause(2);


% Grab the frames:
tic
fprintf('Grabbing %d seconds at %d FPS...\n', seconds, newFramesPerSec);
% for index = 1:FRAMECONSECorig
fc = 1;
for index = 1:FRAMECONSECorig
    if mod(index,skip)==0
        capArray(:, :, :, fc) = fgrabm_grab();
    else trashArray = fgrabm_grab();continue;
    end
    fc = fc + 1;
end
toc

% Shut down capturing:
fgrabm_shutdown

imagesc(capArray(:,:,1,1));colormap('gray')

    clipSuffix = 1;

if saveMAT
    save([ fileDir filePrefix '_' clipSuffix '.mat'],'capArray')%9.5 MB per minute
end

if saveWMV
    video = setdefaults(video,'width',formatInfo.width,'height',formatInfo.height);%values must be in pixels and be even integers
    for k = 1:size(capArray,4);
        video.frames(k) = im2frame(capArray(:,:,:,k));
    end
    video.times( 1:length(video.frames) ) = (1:length(video.frames))/newFramesPerSec;
    mmwrite([fileDir filePrefix '_' clipSuffix  '.wmv'],video)
end


% % % % Now average together the frames and normalize.  We will use a loop here
% % % % and convert to floating point frame by frame so as to avoid precision
% % % % loss.  Although we could cast the entire capArray, that would be more
% % % % expensive than necessary.
% % % fprintf('Calculating average...\n');
% % % outArray = zeros([formatInfo.height formatInfo.width 3]);
% % % for index = 1:FRAMECONSEC
% % %     outArray = outArray + cast(capArray(:, :, :, index), 'double');
% % % end
% % % minVal = min(min(min(outArray)));
% % % maxVal = max(max(max(outArray)));
% % % outArray = (outArray - minVal) ./ (maxVal - minVal);
% % % % Display the image:
% % % fprintf('Displaying result...\n');
% % % image(outArray);
