document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('catalogSearchForm');
    if (!form) return;
    const search = document.getElementById('craftSearch');
    const status = document.getElementById('catalogStatus');
    const products = [...document.querySelectorAll('.product-card')];
    products.forEach(card => { const img=card.querySelector('img'); if(img && !img.complete) img.addEventListener('load', () => card.dataset.imageReady='true', {once:true}); });
    const submitSearch = (value) => {
        search.value = value.trim();
        form.requestSubmit();
    };

    const voiceButton = document.querySelector('.voice-btn');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        voiceButton?.setAttribute('title', 'Voice search is not supported in this browser');
        voiceButton?.addEventListener('click', () => { status.textContent = 'Voice search works in Chrome or Edge. Type a craft name to search.'; });
    } else {
        const recognition = new SpeechRecognition();
        recognition.lang = 'en-IN';
        recognition.interimResults = true;
        recognition.maxAlternatives = 1;
        let finalTranscript = '';
        let voiceFailed = false;
        recognition.onstart = () => { finalTranscript = ''; voiceFailed = false; voiceButton.classList.add('is-listening'); search.value = ''; search.focus(); status.textContent = 'Listening… your words will appear in the search box.'; };
        recognition.onend = () => {
            voiceButton.classList.remove('is-listening');
            if (!voiceFailed && finalTranscript.trim()) {
                search.value = finalTranscript.trim();
                status.textContent = `Heard “${search.value}”. Searching the craft catalog…`;
                form.requestSubmit();
            } else if (!voiceFailed) {
                status.textContent = 'No speech was recognized. Try again or type the craft name.';
            }
        };
        recognition.onerror = (event) => { voiceFailed = true; voiceButton.classList.remove('is-listening'); status.textContent = event.error === 'not-allowed' || event.error === 'service-not-allowed' ? 'Allow microphone and speech recognition access in your browser to use voice search.' : event.error === 'no-speech' ? 'No speech was heard. Try again or type the craft name.' : 'Voice search stopped. Check your microphone or type the craft name.'; };
        recognition.onresult = (event) => {
            let transcript = '';
            let confirmed = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript;
                if (event.results[i].isFinal) confirmed += event.results[i][0].transcript;
            }
            search.value = transcript.trim();
            finalTranscript = confirmed.trim();
        };
        voiceButton?.addEventListener('click', () => { try { recognition.start(); } catch (error) { status.textContent = 'Voice search is already listening. Finish speaking or allow microphone access.'; } });
    }

    const imageInput = document.getElementById('craftImageInput');
    document.querySelector('.image-btn')?.addEventListener('click', () => imageInput.click());
    imageInput?.addEventListener('change', async () => {
        const file = imageInput.files?.[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) { status.textContent = 'Choose an image file to search.'; return; }
        const imageUrl = URL.createObjectURL(file);
        const image = new Image();
        image.onload = () => {
            const canvas = document.createElement('canvas');
            const scale = Math.min(1, 700 / Math.max(image.width, image.height));
            canvas.width = Math.max(1, Math.round(image.width * scale));
            canvas.height = Math.max(1, Math.round(image.height * scale));
            const ctx = canvas.getContext('2d', { willReadFrequently: true });
            ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
            const pixels = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
            const bins = new Map();
            let colorful = 0, warm = 0, dark = 0;
            for (let i=0; i<pixels.length; i+=16) {
                const r=pixels[i], g=pixels[i+1], b=pixels[i+2];
                const max=Math.max(r,g,b), min=Math.min(r,g,b);
                if (max < 65) dark++;
                if (max-min > 70) colorful++;
                if (r > 135 && r > g*1.22 && g > b*1.12) warm++;
                const key=`${Math.round(r/64)*64},${Math.round(g/64)*64},${Math.round(b/64)*64}`;
                bins.set(key,(bins.get(key)||0)+1);
            }
            const tone = warm > colorful*.42 ? 'red orange maroon pink' : colorful > pixels.length/16*.32 ? 'colorful painted patterned' : dark > pixels.length/16*.42 ? 'dark black brown carved' : 'cream white pale';
            const dominant = [...bins.entries()].sort((a,b)=>b[1]-a[1]).slice(0,3).map(x=>x[0]).join(' ');
            const terms = `handicraft traditional saree textile toy artisan ${tone} ${dominant}`;
            const matches = products.map(card => ({card, score: compareImageColors(canvas, card.querySelector('img'))}));
            const topScore = Math.max(0, ...matches.map(match => match.score));
            const cutoff = topScore > .9 ? topScore * .92 : topScore * .97;
            let shown = 0;
            matches.forEach(({card, score}) => { const visible = score >= cutoff && score > 0; card.hidden = !visible; if (visible) shown++; });
            URL.revokeObjectURL(imageUrl);
            status.textContent = shown ? `Showing ${shown} item${shown === 1 ? '' : 's'} on this page with similar colors. For craft recognition across the catalog, search by name.` : `No close color match on this page. Search the catalog by craft name or try another page.`;
        };
        image.onerror = () => { URL.revokeObjectURL(imageUrl); status.textContent = 'Could not read that image. Try another photo.'; };
        image.src = imageUrl;
        status.textContent = `Looking for visually similar pieces to ${file.name}…`;
    });

    function compareImageColors(sourceCanvas, targetImage) {
        if (!targetImage?.complete || !targetImage.naturalWidth) return 0;
        try {
            const sample = document.createElement('canvas'); sample.width = sample.height = 16;
            const ctx = sample.getContext('2d', {willReadFrequently:true});
            ctx.drawImage(sourceCanvas,0,0,16,16);
            const a=ctx.getImageData(0,0,16,16).data;
            ctx.clearRect(0,0,16,16); ctx.drawImage(targetImage,0,0,16,16);
            const b=ctx.getImageData(0,0,16,16).data;
            let distance=0;
            for(let i=0;i<a.length;i+=4) distance+=Math.abs(a[i]-b[i])+Math.abs(a[i+1]-b[i+1])+Math.abs(a[i+2]-b[i+2]);
            return 1-distance/(16*16*3*255);
        } catch { return 0; }
    }

    document.querySelector('.location-btn')?.addEventListener('click', () => {
        if (!navigator.geolocation) { status.textContent = 'Location is unavailable in this browser. Pick a state from the filter.'; return; }
        status.textContent = 'Finding your location…';
        navigator.geolocation.getCurrentPosition(async ({coords}) => {
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${coords.latitude}&lon=${coords.longitude}`, {headers:{'Accept-Language':'en'}});
                const place = await response.json();
                const components = place.address || {};
                const region = components.state || components.region || components.state_district || '';
                const state = [...document.querySelector('[name="state"]').options].map(o=>o.value).find(s=>s.toLowerCase() === region.toLowerCase() || region.toLowerCase().includes(s.toLowerCase()));
                if (state) { document.querySelector('[name="state"]').value = state; form.requestSubmit(); }
                else { status.textContent = region ? `Your location is ${region}; the catalog highlights Indian crafts. Choose a state to explore its traditions.` : 'Could not identify a state. Choose one from the catalog filters.'; }
            } catch { status.textContent = 'Could not look up your state. Choose it from the catalog filters.'; }
        }, (error) => { status.textContent = error.code === 1 ? 'Allow location access to find crafts from your region.' : 'Could not get your location. Choose a state from the catalog filters.'; }, {timeout:10000, maximumAge:300000});
    });

    const cartKey = 'desh_ke_haath_demo_cart';
    const designKey = 'desh_ke_haath_demo_designs';
    const cartCount = document.querySelector('.cart-count');
    const readCart = () => { try { return JSON.parse(localStorage.getItem(cartKey) || '[]'); } catch { return []; } };
    const updateCartCount = () => { const count=readCart().reduce((sum,item)=>sum+item.qty,0); if(cartCount){cartCount.textContent=count;cartCount.hidden=count===0;} };
    updateCartCount();
    document.querySelector('.cart-btn')?.addEventListener('click', () => {
        const cart=readCart();
        if (!cart.length) { status.textContent='Your demo collection is empty. Add a piece you love to get started.'; return; }
        status.textContent=`Your demo collection: ${cart.map(item=>`${item.name} ×${item.qty}`).join(', ')}. Demo only; checkout is not connected.`;
    });
    products.forEach(card => card.querySelector('.quick-add-cart')?.addEventListener('click', () => {
        const item={id:card.dataset.productId,name:card.dataset.productName,state:card.dataset.productState,price:Number(card.dataset.productPrice),image:card.dataset.productImage,qty:1};
        const cart=readCart(), existing=cart.find(product=>product.id===item.id);
        if(existing) existing.qty++; else cart.push(item);
        localStorage.setItem(cartKey,JSON.stringify(cart)); updateCartCount();
        status.textContent=`${item.name} added to your demo collection.`;
    }));

    const readDesigns = () => { try { return JSON.parse(localStorage.getItem(designKey) || '[]'); } catch { return []; } };
    const writeDesigns = designs => localStorage.setItem(designKey, JSON.stringify(designs));
    const renderDesigns = () => {
        const grid=document.querySelector('.products-grid');
        if(!grid) return;
        grid.querySelectorAll('[data-custom-design="true"]').forEach(node=>node.remove());
        readDesigns().forEach(design=>{
            const card=document.createElement('article'); card.className='product-card custom-design-card'; card.dataset.customDesign='true';
            const visual=document.createElement('div'); visual.className='product-image-canvas';
            const image=document.createElement('img'); image.className='product-visual'; image.src=design.image; image.alt=design.name; visual.append(image);
            const tag=document.createElement('span'); tag.className='product-origin-tag'; tag.textContent='CUSTOM CONCEPT'; visual.append(tag);
            const info=document.createElement('div'); info.className='product-master-info';
            const meta=document.createElement('div'); meta.className='product-meta-top'; const category=document.createElement('span'); category.className='product-category-label'; category.textContent=design.status==='accepted'?'VENDOR ACCEPTED':'COMMUNITY DESIGN'; meta.append(category); info.append(meta);
            const title=document.createElement('h3'); title.className='product-title-main'; title.textContent=design.name; info.append(title);
            const story=document.createElement('p'); story.className='product-narrative-snippet'; story.textContent=design.prompt; info.append(story);
            const bottom=document.createElement('div'); bottom.className='product-bottom-row'; const price=document.createElement('span'); price.className='product-valuation'; price.textContent='Demo concept'; bottom.append(price);
            const spatial=document.createElement('button'); spatial.type='button'; spatial.className='spatial-view-btn'; spatial.dataset.spatialView=''; spatial.dataset.name=design.name; spatial.dataset.image=design.image; spatial.setAttribute('aria-label',`Preview ${design.name} in 3D, AR or VR`); spatial.innerHTML='✧ <span>AR / VR</span>'; bottom.append(spatial);
            const add=document.createElement('button'); add.type='button'; add.className='quick-add-cart'; add.textContent='+'; add.setAttribute('aria-label',`Add ${design.name} to demo collection`);
            add.addEventListener('click',()=>{const cart=readCart(), found=cart.find(item=>item.id===design.id); if(found)found.qty++;else cart.push({id:design.id,name:design.name,state:'Custom',price:0,image:design.image,qty:1}); localStorage.setItem(cartKey,JSON.stringify(cart));updateCartCount();status.textContent=`${design.name} added to your demo collection.`;});
            bottom.append(add); info.append(bottom); card.append(visual,info); grid.prepend(card);
        });
    };
    renderDesigns();

    const dialog=document.getElementById('designDialog'), result=document.getElementById('designResult');
    document.querySelector('.design-btn')?.addEventListener('click',()=>dialog?.showModal());
    document.getElementById('designForm')?.addEventListener('submit',async event=>{
        event.preventDefault();
        const prompt=document.getElementById('designPrompt').value.trim();
        if(!prompt) return;
        const generateButton=event.submitter;
        if(generateButton) { generateButton.disabled=true; generateButton.textContent='Creating…'; }
        result.replaceChildren(Object.assign(document.createElement('p'),{className:'design-waiting',textContent:'Creating a product concept from your brief… This can take up to a minute.'}));
        try {
            const response=await fetch('/api/generate-craft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
            const data=await response.json();
            if(!response.ok || !data.image) throw new Error(data.error || 'The image service did not return an image.');
            const preview=new Image();
            preview.alt=`Craft concept: ${prompt}`;
            preview.onload=()=>{
            result.replaceChildren(preview);
            const provider=document.createElement('p'); provider.className='design-note'; provider.textContent=`Generated with ${data.provider}. Review it before listing.`; result.append(provider);
            const listingName=prompt.split(/[,.]/)[0].trim().slice(0,64) || 'New Indian craft concept';
            const listButton=document.createElement('button'); listButton.type='button'; listButton.className='design-submit'; listButton.textContent='List this concept';
            listButton.addEventListener('click',()=>{
                const designs=readDesigns(); const design={id:`design-${Date.now()}`,name:listingName,prompt,image:data.image,status:'pending'}; designs.unshift(design); writeDesigns(designs); renderDesigns();
                listButton.disabled=true; listButton.textContent='Listed in demo catalog';
                const vendor=document.createElement('div'); vendor.className='vendor-review-card';
                const vendorText=document.createElement('p'); vendorText.className='design-note'; vendorText.textContent=`Vendor review queue · ${design.name} · Pending`; vendor.append(vendorText);
                const accept=document.createElement('button'); accept.type='button'; accept.className='design-submit'; accept.textContent='Accept as vendor';
                accept.addEventListener('click',()=>{const current=readDesigns(); const item=current.find(x=>x.id===design.id); if(item)item.status='accepted'; writeDesigns(current); renderDesigns(); vendorText.textContent=`Vendor accepted · ${design.name}`; accept.remove();});
                vendor.append(accept); result.append(vendor);
            });
            result.append(listButton);
            };
            preview.onerror=()=>{result.replaceChildren(Object.assign(document.createElement('p'),{className:'design-note',textContent:'The generated image could not be displayed. Try creating it again.'}));};
            preview.src=data.image;
        } catch(error) {
            result.replaceChildren(Object.assign(document.createElement('p'),{className:'design-note',textContent:error.message || 'Image generation failed. Please try again.'}));
        } finally {
            if(generateButton) { generateButton.disabled=false; generateButton.textContent='Create concept'; }
        }
    });
});
