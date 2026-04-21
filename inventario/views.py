import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, F, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from projects.models import Proyecto
from projects.decorators import cargo_required, ROLES_CAMPO
from .models import Proveedor, Insumo, Requiere, Compra, RequiereLote, calcular_costo_fifo
from .forms import ProveedorForm, InsumoForm, RequerirForm, CompraForm


# ── Proveedores ───────────────────────────────────────────────────────────────

@login_required
def proveedores(request):
    search_nombre = request.GET.get('search_nombre', '')
    page     = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 10
    except ValueError:
        per_page = 10

    qs = Proveedor.objects.filter(activo=True).order_by('nombre')
    if search_nombre:
        qs = qs.filter(nombre__icontains=search_nombre)

    paginator = Paginator(qs, per_page)
    try:
        proveedores_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        proveedores_page = paginator.page(1)

    return render(request, 'proveedores.html', {
        'proveedores': proveedores_page,
        'search_nombre': search_nombre,
        'per_page': per_page,
    })


@login_required
def create_proveedor(request):
    if request.method == 'GET':
        return render(request, 'create_proveedor.html', {'form': ProveedorForm()})
    form = ProveedorForm(request.POST)
    if form.is_valid():
        proveedor = form.save()
        messages.success(request, f'El proveedor {proveedor.nombre} fue registrado exitosamente.')
        return redirect('proveedores')
    return render(request, 'create_proveedor.html', {'form': form})


@login_required
def proveedor_detail(request, id_proveedor):
    proveedor = get_object_or_404(Proveedor, pk=id_proveedor)
    if request.method == 'GET':
        return render(request, 'proveedor_detail.html', {
            'proveedor': proveedor,
            'form': ProveedorForm(instance=proveedor),
        })
    form = ProveedorForm(request.POST, instance=proveedor)
    if form.is_valid():
        form.save()
        messages.success(request, f'El proveedor {proveedor.nombre} fue actualizado exitosamente.')
        return redirect('proveedores')
    return render(request, 'proveedor_detail.html', {'proveedor': proveedor, 'form': form})


@login_required
def deactivate_proveedor(request, id_proveedor):
    proveedor = get_object_or_404(Proveedor, pk=id_proveedor, activo=True)
    if request.method == 'POST':
        proveedor.activo = False
        proveedor.deleted_at = timezone.now()
        proveedor.deleted_by = request.user
        proveedor.save()
        messages.success(request, f'El proveedor {proveedor.nombre} ha sido inhabilitado.')
    return redirect('proveedores')


# ── Insumos ───────────────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_CAMPO)
def insumos(request):
    search_nombre    = request.GET.get('search_nombre', '')
    filter_categoria = request.GET.get('filter_categoria', '')
    filter_stock     = request.GET.get('filter_stock', '')
    page     = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 10
    except ValueError:
        per_page = 10

    qs = Insumo.objects.filter(activo=True).order_by('categoria', 'nombre')
    if search_nombre:
        qs = qs.filter(Q(nombre__icontains=search_nombre) | Q(marca__icontains=search_nombre))
    if filter_categoria:
        qs = qs.filter(categoria=filter_categoria)
    if filter_stock == 'agotado':
        qs = qs.filter(stock__lte=0)
    elif filter_stock == 'bajo':
        qs = qs.filter(stock__gt=0, stock_minimo__gt=0, stock__lte=F('stock_minimo'))
    elif filter_stock == 'ok':
        qs = qs.exclude(stock__lte=0).exclude(stock_minimo__gt=0, stock__lte=F('stock_minimo'))

    paginator = Paginator(qs, per_page)
    try:
        insumos_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        insumos_page = paginator.page(1)

    return render(request, 'insumos.html', {
        'insumos': insumos_page,
        'search_nombre': search_nombre,
        'filter_categoria': filter_categoria,
        'filter_stock': filter_stock,
        'categorias': Insumo.CATEGORIA_CHOICES,
        'per_page': per_page,
    })


@login_required
def create_insumo(request):
    if request.method == 'GET':
        return render(request, 'create_insumo.html', {'form': InsumoForm()})
    form = InsumoForm(request.POST)
    if form.is_valid():
        insumo = form.save()
        messages.success(request, f'El insumo {insumo.nombre} fue registrado exitosamente.')
        return redirect('insumos')
    return render(request, 'create_insumo.html', {'form': form})


@login_required
def insumo_detail(request, id_insumo):
    insumo = get_object_or_404(Insumo, pk=id_insumo)
    if request.method == 'GET':
        return render(request, 'insumo_detail.html', {
            'insumo': insumo,
            'form': InsumoForm(instance=insumo),
        })
    form = InsumoForm(request.POST, instance=insumo)
    if form.is_valid():
        form.save()
        messages.success(request, f'El insumo {insumo.nombre} fue actualizado exitosamente.')
        return redirect('insumos')
    return render(request, 'insumo_detail.html', {'insumo': insumo, 'form': form})


@login_required
def insumo_view(request, id_insumo):
    insumo = get_object_or_404(Insumo, pk=id_insumo)
    historial_precios = (
        Compra.objects
        .filter(insumo=insumo, activo=True)
        .select_related('proveedor')
        .order_by('-fecha', '-created')
    )
    proyectos_asignados = (
        Requiere.objects
        .filter(insumo=insumo, activo=True)
        .select_related('proyecto')
        .prefetch_related('lotes__compra')
        .order_by('-created')
    )
    return render(request, 'insumo_view.html', {
        'insumo': insumo,
        'historial_precios': historial_precios,
        'proyectos_asignados': proyectos_asignados,
    })


@login_required
def deactivate_insumo(request, id_insumo):
    insumo = get_object_or_404(Insumo, pk=id_insumo, activo=True)
    if request.method == 'POST':
        insumo.activo = False
        insumo.deleted_at = timezone.now()
        insumo.deleted_by = request.user
        insumo.save()
        messages.success(request, f'El insumo {insumo.nombre} ha sido inhabilitado.')
    return redirect('insumos')


# ── Requiere (insumos por proyecto) ──────────────────────────────────────────

def _lotes_fifo_json(insumos_activos, excluir_requiere_pk=None):
    """Construye el JSON de lotes FIFO por insumo para el cálculo client-side.
    Usa 2 queries en lugar de O(N×M): una para consumidos agregados, otra para compras.
    """
    insumo_ids = [i.id for i in insumos_activos]
    resultado = {str(i.id): [] for i in insumos_activos}
    if not insumo_ids:
        return json.dumps(resultado)

    # 1 query: total consumido por compra para todos los insumos relevantes
    consumed_qs = RequiereLote.objects.filter(
        requiere__activo=True,
        compra__insumo_id__in=insumo_ids,
    )
    if excluir_requiere_pk:
        consumed_qs = consumed_qs.exclude(requiere_id=excluir_requiere_pk)
    consumed_by_compra = dict(
        consumed_qs.values('compra_id').annotate(t=Sum('cantidad')).values_list('compra_id', 't')
    )

    # 1 query: todas las compras activas de los insumos relevantes, ordenadas FIFO
    for compra in Compra.objects.filter(insumo_id__in=insumo_ids, activo=True).order_by('insumo_id', 'fecha', 'created'):
        consumido = consumed_by_compra.get(compra.id, 0)
        disponible = max(0, compra.cantidad - consumido)
        if disponible > 0:
            resultado[str(compra.insumo_id)].append({'d': disponible, 'p': float(compra.costo_unitario)})

    return json.dumps(resultado)


@login_required
def create_requiere(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    if project.estado_proyecto == 'completado':
        messages.error(request, 'No se pueden agregar insumos a un proyecto completado. Los precios quedan bloqueados.')
        return redirect('project_view', id_project=project.id)
    insumos_activos = list(Insumo.objects.filter(activo=True))
    insumos_con_stock = {}
    for i in insumos_activos:
        insumos_con_stock[str(i.id)]      = i.stock
        insumos_con_stock[f'min_{i.id}']  = i.stock_minimo
        insumos_con_stock[f'unit_{i.id}'] = i.unidad_abrev

    ctx = {
        'form': RequerirForm(),
        'project': project,
        'lotes_fifo':      _lotes_fifo_json(insumos_activos),
        'insumos_con_stock': json.dumps(insumos_con_stock),
    }
    if request.method == 'GET':
        return render(request, 'create_requiere.html', ctx)

    form = RequerirForm(request.POST)
    ctx['form'] = form
    if form.is_valid():
        insumo   = form.cleaned_data['insumo']
        cantidad = form.cleaned_data['cantidad']

        if Requiere.objects.filter(proyecto=project, insumo=insumo, activo=True).exists():
            form.add_error('insumo', f'"{insumo.nombre}" ya está asignado a este proyecto.')
            return render(request, 'create_requiere.html', ctx)

        try:
            lotes_consumo = calcular_costo_fifo(insumo, cantidad)
        except ValueError as e:
            form.add_error('cantidad', str(e))
            return render(request, 'create_requiere.html', ctx)

        costo_total = sum(l['cantidad'] * l['compra'].costo_unitario for l in lotes_consumo)

        requiere = form.save(commit=False)
        requiere.proyecto = project
        requiere.save()

        for lote_info in lotes_consumo:
            RequiereLote.objects.create(
                requiere=requiere,
                compra=lote_info['compra'],
                cantidad=lote_info['cantidad'],
            )

        messages.success(request, f'Insumo "{requiere.insumo.nombre}" agregado al proyecto (total: Bs. {costo_total}).')
        return redirect('project_view', id_project=project.id)
    return render(request, 'create_requiere.html', ctx)


@login_required
def requiere_detail(request, id_requiere):
    requiere = get_object_or_404(Requiere.objects.prefetch_related('lotes__compra'), pk=id_requiere)
    project = requiere.proyecto
    if project.estado_proyecto == 'completado':
        messages.error(request, 'Los insumos de un proyecto completado no pueden modificarse. Los precios están bloqueados.')
        return redirect('project_view', id_project=project.id)
    insumos_activos = list(Insumo.objects.filter(activo=True))
    insumos_con_stock = {}
    for i in insumos_activos:
        insumos_con_stock[str(i.id)]      = i.stock
        insumos_con_stock[f'min_{i.id}']  = i.stock_minimo
        insumos_con_stock[f'unit_{i.id}'] = i.unidad_abrev

    ctx = {
        'requiere': requiere,
        'project': project,
        'lotes_fifo':      _lotes_fifo_json(insumos_activos, excluir_requiere_pk=requiere.pk),
        'insumos_con_stock': json.dumps(insumos_con_stock),
    }
    if request.method == 'GET':
        ctx['form'] = RequerirForm(instance=requiere)
        return render(request, 'requiere_detail.html', ctx)

    form = RequerirForm(request.POST, instance=requiere)
    ctx['form'] = form
    if form.is_valid():
        insumo   = form.cleaned_data['insumo']
        cantidad = form.cleaned_data['cantidad']
        try:
            lotes_consumo = calcular_costo_fifo(insumo, cantidad, excluir_requiere_pk=requiere.pk)
        except ValueError as e:
            form.add_error('cantidad', str(e))
            return render(request, 'requiere_detail.html', ctx)

        costo_total = sum(l['cantidad'] * l['compra'].costo_unitario for l in lotes_consumo)

        # Desactivar lotes anteriores (soft-delete) antes de crear los nuevos
        RequiereLote.objects.filter(requiere=requiere).update(
            activo=False, deleted_at=timezone.now(), deleted_by=request.user
        )

        updated = form.save()

        for lote_info in lotes_consumo:
            RequiereLote.objects.create(
                requiere=updated,
                compra=lote_info['compra'],
                cantidad=lote_info['cantidad'],
            )

        messages.success(request, 'Insumo del proyecto actualizado correctamente.')
        return redirect('project_view', id_project=project.id)
    return render(request, 'requiere_detail.html', ctx)


@login_required
def deactivate_requiere(request, id_requiere):
    requiere = get_object_or_404(Requiere, pk=id_requiere)
    project = requiere.proyecto
    id_project = project.id
    if project.estado_proyecto == 'completado':
        messages.error(request, 'No se pueden eliminar insumos de un proyecto completado.')
        return redirect('project_view', id_project=id_project)
    if request.method == 'POST':
        requiere.activo = False
        requiere.deleted_at = timezone.now()
        requiere.deleted_by = request.user
        requiere.save()
        messages.success(request, f'{requiere.cantidad} unidad(es) de "{requiere.insumo.nombre}" devueltas al stock.')
    return redirect('project_view', id_project=id_project)


# ── Compras (Realizar) ────────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_CAMPO)
def compras(request):
    search   = request.GET.get('search', '')
    page     = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)

    try:
        page = max(int(page), 1)
    except ValueError:
        page = 1
    try:
        per_page = int(per_page) if int(per_page) in [10, 20, 50, 100] else 10
    except ValueError:
        per_page = 10

    qs = Compra.objects.filter(activo=True).select_related('proveedor', 'insumo').order_by('-fecha')
    if search:
        qs = qs.filter(
            Q(insumo__nombre__icontains=search) | Q(proveedor__nombre__icontains=search)
        )

    paginator = Paginator(qs, per_page)
    try:
        compras_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        compras_page = paginator.page(1)

    return render(request, 'compras.html', {
        'compras': compras_page,
        'search': search,
        'per_page': per_page,
    })


@login_required
def create_compra(request):
    insumos_qs = Insumo.objects.filter(activo=True)
    insumos_unidades = json.dumps({str(i.id): i.unidad_abrev for i in insumos_qs})
    insumos_unidades_display = json.dumps({str(i.id): i.get_unidad_medida_display() for i in insumos_qs})
    ctx = {'form': CompraForm(), 'insumos_unidades': insumos_unidades, 'insumos_unidades_display': insumos_unidades_display}
    if request.method == 'GET':
        return render(request, 'create_compra.html', ctx)
    form = CompraForm(request.POST)
    if form.is_valid():
        compra = form.save()
        messages.success(request, f'Compra registrada: {compra.insumo.nombre} x{compra.cantidad} de {compra.proveedor.nombre}.')
        return redirect('compras')
    ctx['form'] = form
    return render(request, 'create_compra.html', ctx)


@login_required
def compra_detail(request, id_compra):
    compra = get_object_or_404(Compra, pk=id_compra)
    insumos_qs = Insumo.objects.filter(activo=True)
    insumos_unidades = json.dumps({str(i.id): i.unidad_abrev for i in insumos_qs})
    insumos_unidades_display = json.dumps({str(i.id): i.get_unidad_medida_display() for i in insumos_qs})
    ctx = {'compra': compra, 'insumos_unidades': insumos_unidades, 'insumos_unidades_display': insumos_unidades_display}
    if request.method == 'GET':
        ctx['form'] = CompraForm(instance=compra)
        return render(request, 'compra_detail.html', ctx)
    form = CompraForm(request.POST, instance=compra)
    if form.is_valid():
        compra = form.save()
        messages.success(request, 'Compra actualizada correctamente.')
        return redirect('compras')
    ctx['form'] = form
    return render(request, 'compra_detail.html', ctx)


@login_required
def deactivate_compra(request, id_compra):
    compra = get_object_or_404(Compra, pk=id_compra, activo=True)
    if request.method == 'POST':
        compra.activo = False
        compra.deleted_at = timezone.now()
        compra.deleted_by = request.user
        compra.save()
        messages.success(request, 'Compra inhabilitada correctamente.')
    return redirect('compras')


# ── Reporte de Inventario ─────────────────────────────────────────────────────

@login_required
@cargo_required(*ROLES_CAMPO)
def inventario_report(request):
    search_nombre    = request.GET.get('search_nombre', '').strip()
    filter_categoria = request.GET.get('filter_categoria', '')
    filter_stock     = request.GET.get('filter_stock', '')
    per_page = int(request.GET.get('per_page', 10))
    if per_page not in (10, 20, 50, 100):
        per_page = 10
    page = request.GET.get('page', 1)

    qs = Insumo.objects.filter(activo=True).order_by('categoria', 'nombre')
    if search_nombre:
        qs = qs.filter(Q(nombre__icontains=search_nombre) | Q(marca__icontains=search_nombre))
    if filter_categoria:
        qs = qs.filter(categoria=filter_categoria)
    if filter_stock == 'agotado':
        qs = qs.filter(stock__lte=0)
    elif filter_stock == 'bajo':
        qs = qs.filter(stock__gt=0, stock_minimo__gt=0, stock__lte=F('stock_minimo'))
    elif filter_stock == 'ok':
        qs = qs.exclude(stock__lte=0).exclude(stock_minimo__gt=0, stock__lte=F('stock_minimo'))

    insumos_list = list(qs)
    for ins in insumos_list:
        ins.valor_stock = ins.stock * ins.ultimo_precio_compra
        ins.estado = ins.stock_status  # 'agotado', 'bajo', 'ok'

    total_insumos = len(insumos_list)
    cnt_agotados  = sum(1 for i in insumos_list if i.estado == 'agotado')
    cnt_bajo      = sum(1 for i in insumos_list if i.estado == 'bajo')
    cnt_ok        = sum(1 for i in insumos_list if i.estado == 'ok')
    valor_total   = sum(i.valor_stock for i in insumos_list)

    # ── Datos para gráficos (solo en vista HTML, no en PDF/Excel) ─────────────
    # Gráfico 1: cantidad de ítems por categoría
    from collections import defaultdict
    cat_counts  = defaultdict(int)
    cat_valores = defaultdict(float)
    cat_labels_map = dict(Insumo.CATEGORIA_CHOICES)
    for ins in insumos_list:
        label = cat_labels_map.get(ins.categoria, ins.categoria)
        cat_counts[label]  += 1
        cat_valores[label] += float(ins.valor_stock)

    chart_cat_labels = json.dumps(list(cat_counts.keys()))
    chart_cat_counts = json.dumps(list(cat_counts.values()))
    chart_cat_valores = json.dumps([round(v, 2) for v in cat_valores.values()])

    # Gráfico 2: top 8 insumos por valor en stock
    top_insumos = sorted(insumos_list, key=lambda x: x.valor_stock, reverse=True)[:8]
    chart_top_labels = json.dumps([f"{i.nombre[:20]}" for i in top_insumos])
    chart_top_valores = json.dumps([float(i.valor_stock) for i in top_insumos])

    # PDF/Excel: lista completa; HTML: paginada
    if 'pdf' in request.GET or 'excel' in request.GET:
        insumos_page = None
    else:
        paginator = Paginator(insumos_list, per_page)
        try:
            insumos_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            insumos_page = paginator.page(1)
        insumos_list = list(insumos_page.object_list)

    context = {
        'insumos':           insumos_list,
        'total_insumos':     total_insumos,
        'cnt_agotados':      cnt_agotados,
        'cnt_bajo':          cnt_bajo,
        'cnt_ok':            cnt_ok,
        'valor_total':       valor_total,
        'search_nombre':     search_nombre,
        'filter_categoria':  filter_categoria,
        'filter_stock':      filter_stock,
        'categorias':        Insumo.CATEGORIA_CHOICES,
        'insumos_page':      insumos_page,
        'per_page':          per_page,
        'now':               timezone.now(),
        'generado_por':      request.user.get_full_name() or request.user.username,
        'chart_cat_labels':  chart_cat_labels,
        'chart_cat_counts':  chart_cat_counts,
        'chart_cat_valores': chart_cat_valores,
        'chart_top_labels':  chart_top_labels,
        'chart_top_valores': chart_top_valores,
    }

    if 'pdf' in request.GET:
        template = get_template('inventario_report_pdf.html')
        html = template.render(context)
        response = HttpResponse(content_type='application/pdf')
        disposition = 'attachment' if 'download' in request.GET else 'inline'
        response['Content-Disposition'] = f'{disposition}; filename="reporte_inventario.pdf"'
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('Error al generar el PDF', status=500)
        return response

    if 'excel' in request.GET:
        NUM_COLS = 8
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Inventario'

        title_fill  = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        title_font  = Font(bold=True, size=14, color='D4B84A')
        info_fill   = PatternFill(start_color='1B4D90', end_color='1B4D90', fill_type='solid')
        info_font   = Font(size=9, color='FFFFFF')
        header_fill = PatternFill(start_color='0F2D5A', end_color='0F2D5A', fill_type='solid')
        header_font = Font(bold=True, color='D4B84A', size=10)
        alt_fill    = PatternFill(start_color='EFF2F8', end_color='EFF2F8', fill_type='solid')
        total_fill  = PatternFill(start_color='E8EDF5', end_color='E8EDF5', fill_type='solid')
        total_font  = Font(bold=True, size=10, color='0F2D5A')
        center      = Alignment(horizontal='center', vertical='center')
        left        = Alignment(horizontal='left',   vertical='center')
        right_al    = Alignment(horizontal='right',  vertical='center')
        cell_border = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='thin', color='C0C8D8'),  bottom=Side(style='thin', color='C0C8D8'),
        )
        total_border = Border(
            left=Side(style='thin', color='C0C8D8'), right=Side(style='thin', color='C0C8D8'),
            top=Side(style='medium', color='0F2D5A'), bottom=Side(style='medium', color='0F2D5A'),
        )
        money_fmt = '#,##0.00'

        ws.append(['Reporte de Inventario — SOBOTEC S.R.L.'])
        ws.merge_cells(f'A1:{openpyxl.utils.get_column_letter(NUM_COLS)}1')
        ws['A1'].font = title_font; ws['A1'].fill = title_fill
        ws['A1'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[1].height = 26

        gen_por  = request.user.get_full_name() or request.user.username
        info_str = f'Generado por: {gen_por}  |  Fecha: {timezone.now().strftime("%d/%m/%Y %H:%M")}'
        if search_nombre:      info_str += f'  |  Nombre: {search_nombre}'
        if filter_categoria:   info_str += f'  |  Categoría: {filter_categoria}'
        if filter_stock:       info_str += f'  |  Stock: {filter_stock}'
        ws.append([info_str])
        ws.merge_cells(f'A2:{openpyxl.utils.get_column_letter(NUM_COLS)}2')
        ws['A2'].font = info_font; ws['A2'].fill = info_fill
        ws['A2'].alignment = Alignment(horizontal='left', vertical='center', indent=1)
        ws.row_dimensions[2].height = 18

        ws.append([])
        ws.row_dimensions[3].height = 6

        headers = ['Categoría', 'Nombre', 'Marca / Modelo', 'Stock Actual',
                   'Stock Mínimo', 'Estado', 'Costo Unit. (Bs.)', 'Valor en Stock (Bs.)']
        ws.append(headers)
        for cell in ws[4]:
            cell.font = header_font; cell.fill = header_fill
            cell.alignment = center; cell.border = cell_border
        ws.row_dimensions[4].height = 22

        last_row = 4
        for i, ins in enumerate(insumos_list, start=5):
            marca_modelo = ins.marca
            if ins.modelo:
                marca_modelo += f' / {ins.modelo}'
            estado_str = {'agotado': 'Sin Stock', 'bajo': 'Stock Bajo', 'ok': 'OK'}.get(ins.estado, ins.estado)
            ws.append([
                ins.get_categoria_display(),
                ins.nombre,
                marca_modelo,
                ins.stock,
                ins.stock_minimo,
                estado_str,
                float(ins.ultimo_precio_compra),
                float(ins.valor_stock),
            ])
            row_fill = alt_fill if i % 2 == 0 else None
            for j, cell in enumerate(ws[i], start=1):
                if row_fill: cell.fill = row_fill
                cell.border = cell_border
                if j in (4, 5): cell.alignment = center
                elif j in (7, 8):
                    cell.alignment = right_al; cell.number_format = money_fmt
                else: cell.alignment = left
            ws.row_dimensions[i].height = 16
            last_row = i

        total_row = last_row + 1
        ws.append(['', 'TOTAL', '', '', '', '', '', float(valor_total)])
        for j, cell in enumerate(ws[total_row], start=1):
            cell.font = total_font; cell.fill = total_fill; cell.border = total_border
            if j == 8:
                cell.alignment = right_al; cell.number_format = money_fmt
            else:
                cell.alignment = left
        ws.row_dimensions[total_row].height = 18

        col_widths = [20, 28, 22, 14, 14, 12, 18, 20]
        for col_idx, width in enumerate(col_widths, start=1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

        ws.freeze_panes = 'A5'
        ws.auto_filter.ref = f'A4:{openpyxl.utils.get_column_letter(NUM_COLS)}4'

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="reporte_inventario.xlsx"'
        wb.save(response)
        return response

    return render(request, 'inventario_report.html', context)
