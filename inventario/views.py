import json
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from projects.models import Proyecto
from projects.decorators import cargo_required, ROLES_CAMPO
from .models import Proveedor, Insumo, Requiere, Realizar
from .forms import ProveedorForm, InsumoForm, RequerirForm, RealizarForm


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

    paginator = Paginator(qs, per_page)
    try:
        insumos_page = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        insumos_page = paginator.page(1)

    return render(request, 'insumos.html', {
        'insumos': insumos_page,
        'search_nombre': search_nombre,
        'filter_categoria': filter_categoria,
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

@login_required
def create_requiere(request, id_project):
    project = get_object_or_404(Proyecto, pk=id_project)
    insumos_activos = Insumo.objects.filter(activo=True)
    insumos_con_precio = {str(i.id): str(i.costo_promedio) for i in insumos_activos}
    insumos_con_stock  = {str(i.id): i.stock for i in insumos_activos}
    for i in insumos_activos:
        insumos_con_stock[f'min_{i.id}'] = i.stock_minimo

    ctx = {
        'form': RequerirForm(),
        'project': project,
        'insumos_con_precio': json.dumps(insumos_con_precio),
        'insumos_con_stock':  json.dumps(insumos_con_stock),
    }
    if request.method == 'GET':
        return render(request, 'create_requiere.html', ctx)

    form = RequerirForm(request.POST)
    ctx['form'] = form
    if form.is_valid():
        requiere = form.save(commit=False)
        requiere.proyecto = project
        requiere.save()
        messages.success(request, f'Insumo "{requiere.insumo.nombre}" agregado al proyecto.')
        return redirect('project_view', id_project=project.id)
    return render(request, 'create_requiere.html', ctx)


@login_required
def requiere_detail(request, id_requiere):
    requiere = get_object_or_404(Requiere, pk=id_requiere)
    project = requiere.proyecto
    insumos_activos = Insumo.objects.filter(activo=True)
    insumos_con_precio = {str(i.id): str(i.costo_promedio) for i in insumos_activos}

    ctx = {
        'requiere': requiere,
        'project': project,
        'insumos_con_precio': json.dumps(insumos_con_precio),
    }
    if request.method == 'GET':
        ctx['form'] = RequerirForm(instance=requiere)
        return render(request, 'requiere_detail.html', ctx)

    form = RequerirForm(request.POST, instance=requiere)
    ctx['form'] = form
    if form.is_valid():
        form.save()
        messages.success(request, 'Insumo del proyecto actualizado correctamente.')
        return redirect('project_view', id_project=project.id)
    return render(request, 'requiere_detail.html', ctx)


@login_required
def deactivate_requiere(request, id_requiere):
    requiere = get_object_or_404(Requiere, pk=id_requiere)
    id_project = requiere.proyecto.id
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

    qs = Realizar.objects.select_related('proveedor', 'insumo').order_by('-fecha')
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
def create_realizar(request):
    if request.method == 'GET':
        return render(request, 'create_realizar.html', {'form': RealizarForm()})
    form = RealizarForm(request.POST)
    if form.is_valid():
        compra = form.save()
        messages.success(request, f'Compra registrada: {compra.insumo.nombre} x{compra.cantidad} de {compra.proveedor.nombre}.')
        return redirect('compras')
    return render(request, 'create_realizar.html', {'form': form})


@login_required
def realizar_detail(request, id_realizar):
    compra = get_object_or_404(Realizar, pk=id_realizar)
    if request.method == 'GET':
        return render(request, 'realizar_detail.html', {
            'compra': compra,
            'form': RealizarForm(instance=compra),
        })
    form = RealizarForm(request.POST, instance=compra)
    if form.is_valid():
        compra = form.save()
        messages.success(request, 'Compra actualizada correctamente.')
        return redirect('compras')
    return render(request, 'realizar_detail.html', {'compra': compra, 'form': form})


@login_required
def deactivate_realizar(request, id_realizar):
    compra = get_object_or_404(Realizar, pk=id_realizar, activo=True)
    if request.method == 'POST':
        compra.activo = False
        compra.deleted_at = timezone.now()
        compra.deleted_by = request.user
        compra.save()
        messages.success(request, 'Compra inhabilitada correctamente.')
    return redirect('compras')
