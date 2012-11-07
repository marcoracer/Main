function getSalienceMap(imagefile)
%Final version of salience map creator.

%Written by Seth Koenig 6/1/12; Questions, comments, or known bugs email 
%skoenig@gatech.edu. Based on "Visual Attention for Rapid Scene
%Analysis" by Itti, Koch, and Niebur. 1998(20):11. Their toolbox is available
%@ http://www.saliencytoolbox.net/doc/mdoc/mfiles/makeSaliencyMap.html.

%Input: image file 

%Output: Save file with saliency map normalized with values ranging from 0 
%to 1, where 1 is the maximum salience. Variables 'fullmap' and 'SALIENCEMAP'
%in save file are the combined saliency maps and the layered saliency maps
%saved as a cell array, respectively.

rgb = imread(imagefile);
intensity = mean(double(rgb),3);

filtimg = cell(1,9);
rgbfimg = cell(1,9);
for i = 1:length(filtimg)
    if i == 1;
        filtimg{i} = intensity;
        rgbfimg{i} = rgb;
    else
        filtimg{i} = impyramid(filtimg{i-1},'reduce'); %creates gaussian pyramids
        rgbfimg{i} = impyramid(rgbfimg{i-1},'reduce');
    end
end

%---------Feature Maps---------%
c = 2:4;
delta = 3:4;
center = [1 -1];% on center or off center
map = [];
for i = 1:2;
    for ii = 1:3;
        for iii = 1:2;
            M = -1*center(i)*ones(c(ii)+2*delta(iii));
            M = M/((2*delta(iii)+c(ii))^2-c(ii)^2);
            M(1+delta(iii):end-delta(iii),1+delta(iii):end-delta(iii)) = center(i)/(c(ii)^2);
            map = [map {M}];
        end
    end
end

SALIENCEMAP = {};
for pyramids = 1:length(filtimg)
    
    %---------Intensity contrast---------%
    Intensitycontrast = {};
    for i = 1:length(map);
        temp =imfilter(filtimg{pyramids},map{i},'replicate');
        for blah = 1:pyramids-1;
            temp = impyramid(temp,'expand'); %expands pyramids back to full size
        end
        Intensitycontrast{i} = imresize(temp,[size(intensity,1) size(intensity,2)]);
    end
    
    %---------Global Intensity Contrast---------%
    globalI = zeros(size(Intensitycontrast{1},1),size(Intensitycontrast{1},2));
    for i = 1:length(Intensitycontrast);
        IC = abs(Intensitycontrast{i});
        IC = IC - min(min(IC));
        IC = 256*IC/max(max(IC));
        IC = IC*(256-mean(mean(IC)))^2;
        globalI = globalI + IC;
    end
    globalI = globalI - min(min(globalI));
    globalI = 256*globalI/max(max(globalI));
    globalI = globalI*(256-mean(mean(globalI)))^2;
    
    %---------Hue Layers and Color Contrast---------%
    Inorm = filtimg {pyramids}/max(max(filtimg {pyramids})); %normalize who's to intensity
    Inorm(Inorm<0.1) = 1;
    rgb = rgbfimg{pyramids};
    r = double(rgb(:,:,1)); g = double(rgb(:,:,2)); b = double(rgb(:,:,3));
    
    R = (r - (g+b)/2)./Inorm; 
    G = (g - (r+b)/2)./Inorm; 
    B = (b - (r+g)/2)./Inorm; 
    Y = ((r+g)/2 - abs((r-g))/2  - b)./Inorm;
    
    %---------Red/Green and Blue/Yellow contrast---------
    RGBY = {};
    for i = 1:2
        if i == 1;
            layer = R-G;
        else
            layer = B-Y;
        end
        for ii = 1:length(map);
            temp =imfilter(layer,map{i},'replicate');
            for blah = 1:pyramids-1;
                temp = impyramid(temp,'expand');
            end
            RGBY{i}{ii} = imresize(temp,[size(intensity,1) size(intensity,2)]);
        end
    end
    
    globalclr = zeros(size(RGBY{i}{1},1),size(RGBY{i}{1},2));
    titles = [{'Red Green Contrast'} {'Blue Yellow Contrast'}];
    for i = 1:2;
        cont = zeros(size(RGBY{i}{1},1),size(RGBY{i}{1},2));
        for ii = 1:length(RGBY{i});
            clr = RGBY{i}{ii};
            clr = clr-min(min(clr));
            clr = 256/max(max(clr))*clr;
            clr = clr*(256-mean(mean(clr)))^2;
            cont = cont+clr;
        end
    end
    globalclr = globalclr + cont;
    globalclr = globalclr - min(min(globalclr));
    globalclr = 256/max(max(globalclr))*globalclr;
    globalclr = globalclr*(256-mean(mean(globalclr)))^2;
    
    %---------orientation Contrast---------%
    orientcontrast = {};
    THETA = [0 pi/4 pi/2 3*pi/4];%aka 0, 45, 90, 135 degree orientations
    for sig = 1:8; %0 does not work -> get lots of NaNs
        for t = 1:length(THETA);
            theta = THETA(t);
            for i = 1:2;
                for ii = 1:3;
                    [xc,yc] = meshgrid(-c(ii):c(ii));
                    [xs,ys] = meshgrid(-c(ii)-delta(i):c(ii)+delta(i));
                    
                    x_theta=xc*cos(theta)+yc*sin(theta);
                    y_theta=-xc*sin(theta)+yc*cos(theta);
                    gaborc = exp(-(x_theta.^2 + y_theta.^2)/(2*sig^2)).*cos(2*pi*x_theta/4);
                    gaborc = gaborc/abs(sum(sum(gaborc)));
                    
                    x_theta=xs*cos(theta)+ys*sin(theta);
                    y_theta=-xs*sin(theta)+ys*cos(theta);
                    gabors = exp(-(x_theta.^2 + y_theta.^2)/(2*sig^2)).*cos(2*pi*x_theta/4);
                    cs = floor((length(gabors)-length(gaborc))/2);
                    gabors(1+cs:end-cs,1+cs:end-cs) = 0;
                    gabors = gabors/sum(sum(gabors));
                    if i == 1; %on center
                        gabors = -gabors;
                        gabors(1+cs:end-cs,1+cs:end-cs) = gaborc;
                    else % off center
                        gabors(1+cs:end-cs,1+cs:end-cs) = -gaborc;
                    end
                    temp = imfilter(filtimg{pyramids},gabors,'replicate');
                    for blah = 1:pyramids-1;
                        temp = impyramid(temp,'expand');
                    end
                    orientcontrast = [orientcontrast {imresize(temp,[size(intensity,1) size(intensity,2)])}];
                end
            end
        end
    end
    
    %---------Global Orientation Contrast---------%
    globalO = zeros(size(orientcontrast{1},1),size(orientcontrast{1},2));
    for l = 1:length(orientcontrast)
        OC = abs(orientcontrast{l});
        OC = OC-min(min(OC));
        OC = 256*OC/max(max(OC));
        OC = OC*(256-mean(mean(OC)))^2;
        globalO = globalO + OC;
    end
    globalO = globalO-min(min(globalO));
    globalO = 256*globalO/max(max(globalO));
    globalO = globalO*(256-mean(mean(globalO)))^2;
    
    %---------Salience Map---------%
    saliencemap = 1/3*(globalO + globalI + globalclr);
    SALIENCEMAP{pyramids} = saliencemap;
end

fullmap = SALIENCEMAP{1};
for i = 2:length(SALIENCEMAP)
    fullmap = fullmap + SALIENCEMAP{i};
end
fullmap = fullmap - min(min(fullmap));
fullmap = fullmap/max(max(fullmap));
fullmap = fullmap*(1-mean(mean(fullmap)))^2;
fullmap = fullmap/max(max(fullmap));

%----Display Output----%
figure
imagesc(fullmap),title('Total Saliency Map')
saveas(gcf,[imagefile(1:end-4) '-saliencemap'], 'jpg') %saves output image

%---Save Saliency Map and Layers---%
d = date;
savefile = [imagefile(1:end-4) '-saliencemap-' d];
save([savefile],'fullmap','SALIENCEMAP')
end