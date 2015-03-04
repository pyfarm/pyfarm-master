function hide_parent(element) {
    element.parentNode.style.display='none';
    };

$(document).ready(function() {
    $('.dropdown-menu').on('click', function(e) {
        if($(this).hasClass('dropdown-menu-form')) {
            e.stopPropagation();
        }
    });
});
