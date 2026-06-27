const icon="a";
const meta={color:"red"};
const finalIconUrl="a";
const _hesc=x=>x;
const customIconHtml = `<img src="${_hesc(finalIconUrl)}" style="width:100%;height:100%;object-fit:cover;border-radius:12px;" onerror="this.outerHTML='<i class=\\'fas ${icon}\\' style=\\'color:${meta.color};font-size:18px;\\'></i>'">`;
console.log(customIconHtml);
